# FaultMaven Copilot Verification Checklist

**Purpose:** Verify that `faultmaven-copilot` implements the Capabilities API and deployment mode detection as specified in Design v2.0.

**Status:** ❓ Requires Source Code Review

---

## Critical Requirements (Design v2.0)

The browser extension **must** implement capabilities-driven architecture to support both self-hosted and enterprise deployments from a single codebase.

---

## Verification Tasks

### 1. Capabilities API Integration

**Requirement:** Extension calls `/v1/meta/capabilities` on startup

**Files to Check:**
- `src/lib/api-client.ts` or similar API client
- `src/entrypoints/background/` or background script
- Any initialization/startup code

**What to Look For:**

```typescript
// Should exist somewhere in the codebase
const fetchCapabilities = async () => {
  const response = await fetch(`${API_URL}/v1/meta/capabilities`);
  const capabilities = await response.json();
  return capabilities;
};
```

**Verification Steps:**

- [ ] Search codebase for `/v1/meta/capabilities` string
- [ ] Verify it's called on extension startup/initialization
- [ ] Check if response is stored (localStorage, Redux, context)
- [ ] Verify error handling (what if endpoint fails?)

**Expected Behavior:**
- ✅ Endpoint called on first load
- ✅ Response cached (don't call on every page load)
- ✅ Retry logic if initial call fails
- ✅ Fallback to safe defaults if unavailable

---

### 2. Feature Detection and UI Adaptation

**Requirement:** UI shows/hides features based on capabilities response

**Files to Check:**
- React components in `src/shared/ui/` or similar
- Main chat interface component
- Settings/configuration components

**What to Look For:**

```typescript
// Example: Conditional rendering based on capabilities
const ChatInterface = () => {
  const { capabilities } = useCapabilities(); // or similar hook

  return (
    <>
      <Chat />

      {capabilities.features.organizations && (
        <OrganizationSelector />
      )}

      {capabilities.features.teams && (
        <TeamSelector />
      )}

      {capabilities.features.sso && (
        <SSOLoginButton />
      )}
    </>
  );
};
```

**Verification Steps:**

- [ ] Search for `capabilities.features` usage
- [ ] Check for conditional rendering based on features
- [ ] Verify these features are checked:
  - [ ] `organizations`
  - [ ] `teams`
  - [ ] `sso`
  - [ ] `chat` (should always be true)
  - [ ] `knowledgeBase` (should always be true)
  - [ ] `cases` (should always be true)

**Expected UI Adaptations:**

| Feature | Self-Hosted (false) | Enterprise (true) |
|---------|---------------------|-------------------|
| Organizations | Hidden | Show org selector |
| Teams | Hidden | Show team selector |
| SSO | Show basic login | Show SSO button |
| Chat | Always shown | Always shown |
| Knowledge Base | Always shown | Always shown |
| Cases | Always shown | Always shown |

---

### 3. Deployment Mode Detection

**Requirement:** Extension adapts behavior based on `deploymentMode`

**Files to Check:**
- Same files as #2 (UI components)
- Any analytics/telemetry code
- Feature flag system

**What to Look For:**

```typescript
// Check deployment mode
if (capabilities.deploymentMode === 'enterprise') {
  // Enable enterprise features
  enableAdvancedAnalytics();
  showTeamFeatures();
} else if (capabilities.deploymentMode === 'self-hosted') {
  // Minimal telemetry, basic features
  disableTelemetry();
  showBasicFeatures();
}
```

**Verification Steps:**

- [ ] Search for `deploymentMode` usage
- [ ] Check what behavior changes between modes
- [ ] Verify telemetry is disabled for self-hosted
- [ ] Check if any enterprise-specific API calls are guarded

---

### 4. API Endpoint Configuration

**Requirement:** Users can configure custom API endpoint

**Files to Check:**
- `src/entrypoints/options/` or settings page
- `.env.example` file
- Configuration storage logic

**What to Look For:**

```typescript
// .env.example
VITE_API_URL=http://127.0.0.1:8000  // Default for self-hosted

// Options page
<input
  type="text"
  value={apiEndpoint}
  onChange={(e) => setApiEndpoint(e.target.value)}
  placeholder="http://localhost:8000"
/>
```

**Verification Steps:**

- [ ] Check if `.env.example` exists (✅ **VERIFIED** - exists)
- [ ] Verify default is `http://127.0.0.1:8000` or `http://localhost:8000` (✅ **VERIFIED**)
- [ ] Check if options page allows override
- [ ] Test if override persists (localStorage/chrome.storage)
- [ ] Verify validation (must be valid URL)

**Expected Behavior:**
- ✅ Default points to localhost (self-hosted)
- ✅ User can change to `https://api.faultmaven.ai` (enterprise)
- ✅ Setting persists across browser sessions
- ✅ Validation prevents invalid URLs

---

### 5. Dashboard URL Integration

**Requirement:** Extension knows where dashboard is located

**What to Look For:**

```typescript
// From capabilities response
{
  "dashboardUrl": "http://localhost:3000" // or "https://app.faultmaven.ai"
}

// Extension uses this to open dashboard
const openDashboard = () => {
  window.open(capabilities.dashboardUrl, '_blank');
};
```

**Verification Steps:**

- [ ] Check if extension opens dashboard (link, button, etc.)
- [ ] Verify it uses `capabilities.dashboardUrl` (not hardcoded)
- [ ] Test with both self-hosted and enterprise URLs

---

### 6. Auth Type Adaptation

**Requirement:** Extension adapts authentication based on auth type

**What to Look For:**

```typescript
// From capabilities
{
  "auth": {
    "type": "jwt",  // or "supabase"
    "loginUrl": "http://localhost:8000/v1/auth/login"
  }
}

// Extension handles different auth flows
if (capabilities.auth.type === 'jwt') {
  // Show username/password form
  showBasicLogin();
} else if (capabilities.auth.type === 'supabase') {
  // Show SSO buttons
  showSSOLogin();
}
```

**Verification Steps:**

- [ ] Check login component
- [ ] Verify it uses `capabilities.auth.type`
- [ ] Test JWT flow (self-hosted)
- [ ] Test SSO flow (enterprise) if possible

---

## Testing Checklist

### Test with Self-Hosted API

**Setup:**
```bash
# Start self-hosted stack
cd faultmaven-deploy
docker compose up -d

# Configure extension
API Endpoint: http://localhost:8000
```

**Test:**
- [ ] Extension calls `http://localhost:8000/v1/meta/capabilities`
- [ ] Response has `deploymentMode: "self-hosted"`
- [ ] Organizations/Teams UI is hidden
- [ ] SSO login is hidden
- [ ] Basic JWT login works
- [ ] Dashboard opens at `http://localhost:3000`

---

### Test with Enterprise API (Simulated)

**Setup:**
```bash
# Mock enterprise capabilities response
# (Requires test server or API mocking)
```

**Test:**
- [ ] Extension calls enterprise capabilities endpoint
- [ ] Response has `deploymentMode: "enterprise"`
- [ ] Organizations/Teams UI is shown
- [ ] SSO login button appears
- [ ] Dashboard opens at enterprise URL

---

## Code Search Commands

To help with verification, run these searches in the copilot repository:

```bash
# Search for capabilities API calls
grep -r "v1/meta/capabilities" src/
rg "capabilities" src/

# Search for feature flags
grep -r "capabilities.features" src/
rg "deploymentMode" src/

# Search for conditional rendering
grep -r "organizations" src/
grep -r "teams" src/
grep -r "sso" src/

# Check API client
cat src/lib/api-client.ts  # or wherever API client is
```

---

## Missing Implementation Checklist

If any of these are missing, they need to be implemented:

### Critical (Must Have)

- [ ] **Capabilities API client** - Fetch `/v1/meta/capabilities`
- [ ] **Startup call** - Call capabilities on extension init
- [ ] **Feature detection** - Conditional UI based on `features` object
- [ ] **Deployment mode handling** - Different behavior for self-hosted vs enterprise

### High Priority (Should Have)

- [ ] **Capabilities caching** - Store response, don't call every time
- [ ] **Error handling** - Fallback if capabilities endpoint fails
- [ ] **Dashboard URL integration** - Use `dashboardUrl` from response
- [ ] **Auth type adaptation** - Different login UI for JWT vs SSO

### Medium Priority (Nice to Have)

- [ ] **Capabilities refresh** - Periodically re-fetch (e.g., daily)
- [ ] **Version checking** - Warn if extension/API versions mismatch
- [ ] **Feature flags UI** - Show users which features are available

---

## Implementation Example (If Missing)

If capabilities API is not implemented, here's what needs to be added:

### 1. Capabilities Client

```typescript
// src/lib/capabilities.ts
interface Capabilities {
  deploymentMode: 'self-hosted' | 'enterprise';
  version: string;
  features: {
    chat: boolean;
    knowledgeBase: boolean;
    cases: boolean;
    organizations: boolean;
    teams: boolean;
    sso: boolean;
  };
  auth: {
    type: 'jwt' | 'supabase';
    loginUrl: string;
  };
  dashboardUrl: string;
}

export async function fetchCapabilities(apiUrl: string): Promise<Capabilities> {
  const response = await fetch(`${apiUrl}/v1/meta/capabilities`);
  if (!response.ok) {
    throw new Error('Failed to fetch capabilities');
  }
  return response.json();
}

// Fallback for self-hosted if endpoint fails
export const defaultCapabilities: Capabilities = {
  deploymentMode: 'self-hosted',
  version: '1.0.0',
  features: {
    chat: true,
    knowledgeBase: true,
    cases: true,
    organizations: false,
    teams: false,
    sso: false,
  },
  auth: {
    type: 'jwt',
    loginUrl: 'http://localhost:8000/v1/auth/login',
  },
  dashboardUrl: 'http://localhost:3000',
};
```

### 2. React Hook

```typescript
// src/hooks/useCapabilities.ts
import { useEffect, useState } from 'react';
import { fetchCapabilities, defaultCapabilities, type Capabilities } from '../lib/capabilities';

export function useCapabilities() {
  const [capabilities, setCapabilities] = useState<Capabilities>(defaultCapabilities);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    fetchCapabilities(apiUrl)
      .then(setCapabilities)
      .catch((err) => {
        console.error('Failed to fetch capabilities, using defaults:', err);
        setError(err);
        setCapabilities(defaultCapabilities);
      })
      .finally(() => setLoading(false));
  }, []);

  return { capabilities, loading, error };
}
```

### 3. Conditional UI

```typescript
// src/components/ChatInterface.tsx
import { useCapabilities } from '../hooks/useCapabilities';

export function ChatInterface() {
  const { capabilities } = useCapabilities();

  return (
    <div>
      <ChatWindow />

      {capabilities.features.organizations && (
        <OrganizationSelector />
      )}

      {capabilities.features.teams && (
        <TeamSelector />
      )}
    </div>
  );
}
```

---

## Summary

**Current Status:**
- ❓ Capabilities API integration: **Unknown** (requires code review)
- ✅ `.env.example` exists with correct default
- ✅ WXT framework (correct for extension)
- ❓ Feature detection: **Unknown**
- ❓ Deployment mode adaptation: **Unknown**

**Next Steps:**
1. Review source code for capabilities implementation
2. Test extension with self-hosted API
3. Verify UI adaptations work
4. Document findings
5. Implement missing features if needed

---

**Verification Status:** 🟡 **Pending Code Review**

This checklist should be used by a developer with access to the `faultmaven-copilot` source code to verify all capabilities API requirements are met.
