"""
Agent module service layer.

This implements the AI assistant with RAG (Retrieval Augmented Generation),
conversation memory, and tool use (function calling).
"""

import json
from typing import AsyncIterator, Optional
from datetime import datetime


class AgentService:
    """
    AI Agent service with RAG and conversation memory.

    The agent orchestrates:
    1. Conversation persistence (via CaseService)
    2. Knowledge retrieval (via KnowledgeService)
    3. LLM generation (via LLMProvider)
    """

    def __init__(
        self,
        llm_provider,
        case_service,
        knowledge_service,
    ):
        """
        Initialize agent service.

        Args:
            llm_provider: LLM provider for AI generation
            case_service: Case service for conversation persistence
            knowledge_service: Knowledge service for RAG
        """
        self.llm = llm_provider
        self.case_service = case_service
        self.knowledge_service = knowledge_service

    async def chat(
        self,
        case_id: str,
        user_id: str,
        message: str,
        stream: bool = False,
        use_rag: bool = True,
        use_tools: bool = True,
    ) -> AsyncIterator[str] | str:
        """
        Chat with the AI assistant.

        This method implements the full RAG + conversation memory pipeline:
        1. Save user message to case
        2. Retrieve context from knowledge base (RAG)
        3. Fetch conversation history from case
        4. Build prompt with system instructions + context + history
        5. Stream LLM response
        6. Save assistant message to case

        Args:
            case_id: Case ID for conversation context
            user_id: User ID for ownership verification
            message: User message
            stream: Whether to stream the response
            use_rag: Whether to use RAG for context retrieval

        Returns:
            Streaming response or complete response
        """
        # Step 1: Save user message
        await self.case_service.add_message(
            case_id=case_id,
            user_id=user_id,
            role="user",
            content=message,
        )

        # Step 2: Gather context via RAG
        context_documents = []
        if use_rag:
            rag_results = await self.knowledge_service.search_knowledge(
                query_text=message,
                user_id=user_id,
                limit=5,
            )
            context_documents = rag_results.get("results", [])

        # Step 3: Fetch conversation history
        history_response = await self.case_service.list_case_messages(
            case_id=case_id,
            user_id=user_id,
            limit=20,  # Last 20 messages for context
        )

        if history_response is None:
            # Case not found or unauthorized
            raise ValueError("Case not found or unauthorized")

        messages, _ = history_response

        # Step 4: Build prompt
        from faultmaven.providers.interfaces import Message, MessageRole

        # System message with RAG context
        system_content = self._build_system_prompt(context_documents)
        system_message = Message(
            role=MessageRole.SYSTEM,
            content=system_content,
        )

        # Conversation history (excluding the message we just added)
        history_messages = []
        for msg in messages[:-1]:  # Exclude last message (the one we just added)
            role = MessageRole.USER if msg.role == "user" else MessageRole.ASSISTANT
            history_messages.append(
                Message(role=role, content=msg.content)
            )

        # Current user message
        user_message = Message(
            role=MessageRole.USER,
            content=message,
        )

        # Combine all messages
        all_messages = [system_message] + history_messages + [user_message]

        # Get available tools if enabled
        tools = None
        if use_tools and not stream:  # Tool calling not supported with streaming yet
            from faultmaven.modules.agent.tools import tool_registry
            tools = tool_registry.get_openai_tools()

        # Step 5: Call LLM
        if stream:
            response_chunks = []

            async def stream_and_save():
                async for chunk in self.llm.stream_completion(
                    messages=all_messages,
                    max_tokens=2000,
                ):
                    response_chunks.append(chunk)
                    yield chunk

                # Step 6: Save assistant message after streaming completes
                complete_response = ''.join(response_chunks)
                await self.case_service.add_message(
                    case_id=case_id,
                    user_id=user_id,
                    role="assistant",
                    content=complete_response,
                )

            return stream_and_save()
        else:
            # Non-streaming response with tool calling support
            response = await self._chat_with_tools(
                messages=all_messages,
                tools=tools,
                max_tokens=2000,
            )

            # Step 6: Save assistant message
            await self.case_service.add_message(
                case_id=case_id,
                user_id=user_id,
                role="assistant",
                content=response,
            )

            return response

    async def _chat_with_tools(
        self,
        messages: list,
        tools: list | None,
        max_tokens: int = 2000,
        max_tool_rounds: int = 5,
    ) -> str:
        """
        Handle chat completion with tool calling support.

        This implements the tool calling loop:
        1. Call LLM with tools
        2. If LLM wants to call a tool, execute it
        3. Feed tool result back to LLM
        4. Repeat until LLM produces a final answer (or max rounds reached)

        Args:
            messages: Conversation messages
            tools: Available tools (OpenAI format)
            max_tokens: Maximum tokens for response
            max_tool_rounds: Maximum number of tool calling rounds

        Returns:
            Final text response from LLM
        """
        from faultmaven.modules.agent.tools import tool_registry
        from faultmaven.providers.interfaces import Message, MessageRole
        import json

        current_messages = messages.copy()

        for round_num in range(max_tool_rounds):
            # Call LLM with tools
            response = await self.llm.chat(
                messages=current_messages,
                max_tokens=max_tokens,
                tools=tools,
            )

            # Check if LLM wants to call a tool
            if response.tool_calls:
                # LLM wants to call one or more tools
                # Add assistant message with tool calls to conversation
                assistant_message = Message(
                    role=MessageRole.ASSISTANT,
                    content=response.content or "",
                )
                current_messages.append(assistant_message)

                # Execute each tool call
                for tool_call in response.tool_calls:
                    try:
                        # Parse tool arguments
                        arguments = json.loads(tool_call.arguments)

                        # Execute the tool
                        tool_result = await tool_registry.execute_tool(
                            name=tool_call.name,
                            arguments=arguments,
                        )

                        # Convert result to JSON string
                        result_content = json.dumps(tool_result)

                    except json.JSONDecodeError as e:
                        result_content = json.dumps({
                            "error": f"Invalid JSON arguments: {str(e)}"
                        })
                    except ValueError as e:
                        result_content = json.dumps({
                            "error": f"Tool not found: {str(e)}"
                        })
                    except Exception as e:
                        result_content = json.dumps({
                            "error": f"Tool execution failed: {str(e)}"
                        })

                    # Add tool result to conversation
                    # OpenAI expects tool messages with role="tool" and tool_call_id
                    tool_message = Message(
                        role="tool",  # Special role for tool results
                        content=result_content,
                        tool_call_id=tool_call.id,  # Link back to the tool call
                    )
                    current_messages.append(tool_message)

                # Continue loop to get final answer from LLM
                continue

            else:
                # No tool calls - LLM produced a final answer
                return response.content

        # Max rounds reached without final answer
        return "I've reached the maximum number of tool calls. Please try asking your question differently."

    def _build_system_prompt(self, context_documents: list) -> str:
        """
        Build system prompt with RAG context.

        Uses XML tags for clear boundary definition to prevent prompt injection.

        Args:
            context_documents: Retrieved documents from knowledge base

        Returns:
            System prompt string
        """
        base_prompt = """You are FaultMaven AI, an expert debugging assistant.

Your purpose is to help developers troubleshoot issues, understand error logs,
and find solutions to technical problems.

Guidelines:
- Be concise and technical
- Cite specific documentation when available
- Ask clarifying questions when needed
- Suggest concrete next steps
"""

        if context_documents:
            # Use XML tags for clearer boundary definition (prevents prompt injection)
            context_section = "\n\n<retrieved_context>\n"

            for i, doc in enumerate(context_documents, 1):
                metadata = doc.get("metadata", {})

                # Robust content extraction: try multiple possible locations
                content = (
                    doc.get("content") or
                    doc.get("document") or
                    metadata.get("content", "")
                )

                filename = metadata.get("filename", "Unknown")
                score = doc.get("score", 0.0)

                context_section += f'<document index="{i}" source="{filename}" relevance="{score:.2f}">\n'
                context_section += f"{content}\n"
                context_section += "</document>\n\n"

            context_section += "</retrieved_context>\n\n"
            context_section += (
                "Instructions: Answer the user's question using the information in "
                "<retrieved_context> above. If the answer is not in the context, say so clearly."
            )

            return base_prompt + context_section

        return base_prompt
