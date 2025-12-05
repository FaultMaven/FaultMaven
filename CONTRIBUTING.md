# Contributing to FaultMaven

Thank you for your interest in contributing to FaultMaven! We're building this in the open and welcome contributions from everyone—whether you're fixing bugs, adding features, improving documentation, or helping others in the community.

---

## What You Can Contribute

All core FaultMaven functionality is open for contribution:

- **AI Troubleshooting Engine:** Prompt engineering, LLM integrations, reasoning improvements
- **Knowledge Base & RAG:** Semantic search, embedding models, knowledge curation
- **Case Management:** Investigation tracking, evidence handling, export formats
- **Session Management:** Chat persistence, context handling
- **Authentication:** JWT improvements, session security
- **Browser Extension:** UI enhancements, new site integrations, context capture
- **Dashboard:** Knowledge base management UI, case visualization
- **LLM Providers:** Add support for new providers (Groq, vLLM, etc.)
- **Documentation:** Guides, examples, tutorials, troubleshooting tips
- **Testing:** Bug reports, test coverage, integration tests

**New here?** Start with issues labeled [`good-first-issue`](https://github.com/search?q=org%3AFaultMaven+label%3A%22good+first+issue%22+state%3Aopen) across all FaultMaven repositories.

---

## How to Contribute

### 1. Find Something to Work On

- **Browse Issues:** Look for [`good-first-issue`](https://github.com/search?q=org%3AFaultMaven+label%3A%22good+first+issue%22+state%3Aopen) or [`help-wanted`](https://github.com/search?q=org%3AFaultMaven+label%3A%22help+wanted%22+state%3Aopen) labels
- **Fix a Bug:** Found a bug? Check if it's already reported, otherwise open an issue
- **Propose a Feature:** Have an idea? Open a discussion or feature request
- **Improve Documentation:** See gaps in the docs? PRs welcome!

### 2. Set Up Your Development Environment

```bash
# Fork and clone the repository you want to contribute to
git clone https://github.com/YOUR_USERNAME/fm-agent-service.git
cd fm-agent-service

# Create a feature branch
git checkout -b feature/your-feature-name
```

### 3. Test Your Changes Locally

Run the full FaultMaven stack to test your changes:

```bash
# Clone the deployment repository
git clone https://github.com/FaultMaven/faultmaven-deploy.git
cd faultmaven-deploy

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or configure Ollama

# Start all services
docker-compose up -d

# Check health
curl http://localhost:8090/health
```

If you're modifying a specific microservice, build it locally:

```bash
# In your service repo (e.g., fm-agent-service)
docker build -t faultmaven/fm-agent-service:local .

# Update docker-compose.yml to use your local image
# services:
#   agent:
#     image: faultmaven/fm-agent-service:local

# Restart the service
cd ../faultmaven-deploy
docker-compose up -d agent

# Test your changes
curl -X POST http://localhost:8090/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message"}'
```

### 4. Submit Your Changes

```bash
# Commit your changes with a clear message
git add .
git commit -m "feat: add support for Groq LLM provider"

# Push to your fork
git push origin feature/your-feature-name

# Open a Pull Request on GitHub
```

### Pull Request Guidelines

- **Clear Description:** Explain what you changed and why
- **Reference Issues:** Link to related issues (e.g., "Fixes #123")
- **Pass Tests:** Ensure your changes don't break existing functionality
- **Update Docs:** Add or update documentation if needed
- **Keep Focused:** One feature or fix per PR (easier to review)

---

## Code Style Guidelines

### Python (Backend Services)

- Follow **PEP 8** style guide
- Use **type hints** for all functions
- Use **async/await** for I/O operations
- Format code with **Black** (line length: 100)
- Sort imports with **isort**

```python
# Good example
async def get_case(case_id: str, db: AsyncSession) -> Case:
    """Retrieve a case by ID.

    Args:
        case_id: The case identifier
        db: Database session

    Returns:
        The case object

    Raises:
        NotFoundError: If case doesn't exist
    """
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise NotFoundError(f"Case {case_id} not found")
    return case
```

### TypeScript (Frontend)

- Use **TypeScript** (no plain JavaScript)
- Follow **React best practices** (hooks, functional components)
- Use **Tailwind CSS** for styling
- Format code with **Prettier**

```typescript
// Good example
interface Case {
  id: string;
  title: string;
  description: string;
  createdAt: Date;
}

const CaseList: React.FC = () => {
  const [cases, setCases] = useState<Case[]>([]);

  useEffect(() => {
    fetchCases().then(setCases);
  }, []);

  return (
    <div className="space-y-4">
      {cases.map(case => (
        <CaseCard key={case.id} case={case} />
      ))}
    </div>
  );
};
```

---

## Commit Message Guidelines

Use **conventional commits** for clear history:

```text
feat: Add RAG reranking support
fix: Resolve session timeout issue
docs: Update deployment guide
refactor: Simplify auth middleware
test: Add integration tests for knowledge service
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no behavior change)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

---

## Non-Code Contributions

You don't need to be a developer to help:

### Documentation

- Improve setup guides
- Add troubleshooting tips
- Create tutorials or examples
- Fix typos or unclear wording

### Community Support

- Answer questions in [GitHub Discussions](https://github.com/FaultMaven/faultmaven/discussions)
- Help reproduce bugs
- Share your use cases and workflows

### Knowledge Base

- Contribute troubleshooting patterns for the Global KB
- Add runbooks for common tech stacks (K8s, PostgreSQL, Redis)
- Share post-mortems (anonymized)

### Testing & Feedback

- Report bugs with detailed reproduction steps
- Test new features and provide feedback
- Suggest UX improvements

---

## Reporting Bugs

1. **Search** existing issues to avoid duplicates
2. **Use** the bug report template (if available)
3. **Include:**
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs. actual behavior
   - Environment details (Docker version, OS, LLM provider)
   - Relevant logs or error messages

**Example:**

```text
**Describe the bug**
The browser extension fails to capture logs from AWS CloudWatch console.

**To Reproduce**
1. Install extension in Chrome
2. Navigate to AWS CloudWatch Logs
3. Click "Ask FaultMaven"
4. Extension shows "No context captured"

**Expected behavior**
Extension should capture visible log entries

**Environment**
- Browser: Chrome 120
- Extension version: 0.2.0
- OS: macOS 14.1
```

---

## Security Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Please report security issues privately by following the instructions in [SECURITY.md](./docs/SECURITY.md).

---

## License

By contributing to FaultMaven, you agree that your contributions will be licensed under the **Apache 2.0 License**.

This means your code can be:

- ✅ Used commercially
- ✅ Modified and distributed
- ✅ Sublicensed

See [LICENSE](LICENSE) for full details.

---

## Community Guidelines

We're committed to maintaining a welcoming and inclusive community:

- **Be respectful:** Treat everyone with kindness and respect
- **Be constructive:** Provide helpful feedback, not just criticism
- **Be patient:** Remember that contributors may be volunteers
- **Be open:** Welcome new ideas and perspectives

For detailed guidelines, see our [Code of Conduct](CODE_OF_CONDUCT.md) (if available).

---

## Getting Help

- **[GitHub Discussions](https://github.com/FaultMaven/faultmaven/discussions)** — Ask questions, share ideas
- **[GitHub Issues](https://github.com/FaultMaven/faultmaven/issues)** — Report bugs, request features
- **[Documentation](./docs/)** — Technical guides and API references
- **[Website](https://faultmaven.ai)** — Product overview and use cases

---

## Thank You

Your contributions help make FaultMaven better for everyone. Whether it's code, documentation, bug reports, or community support—we appreciate your time and effort!

Happy contributing! 🚀

— The FaultMaven Team
