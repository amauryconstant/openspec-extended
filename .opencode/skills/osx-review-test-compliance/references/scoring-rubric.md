# Test Coverage Scoring Rubric

Anchors the subjective confidence levels in `osx-review-test-compliance`. The numbers are guidance; the reasoning behind them is what matters.

## Tiers

| Tier | Range | Match quality |
|---|---|---|
| **High** | 80%+ | Strong semantic match. Test asserts the THEN outcome under the GIVEN conditions named in the scenario. |
| **Medium** | 50–79% | Partial match. Test covers the happy path or a subset of the scenario's clauses. |
| **Low** | <50% | Weak or no match. Coverage gap or orphaned test. |

## Worked examples

### High (≈90%)

> **Scenario**: When a user submits valid credentials, the API SHALL return a 200 with a session token.
> **Test**: `TestLoginWithValidCredentials_Returns200WithSessionToken` — calls POST `/login` with valid fixtures, asserts status==200 and response.token is non-empty.

Score: ~90. Test name and assertions match the scenario clause-for-clause. Test sets up GIVEN, exercises WHEN, asserts THEN.

### High (≈80%)

> **Scenario**: When token expiry is detected, the API SHALL return 401.
> **Test**: `TestTokenExpiry_Returns401` — mints an expired token, calls a protected endpoint, asserts status==401.

Score: ~85. Test asserts the outcome but uses different setup machinery than the scenario describes. Same outcome, slightly different mechanism.

### Medium (≈70%)

> **Scenario**: When a user submits valid credentials, the API SHALL return 200 with a session token. When the same credentials are reused after logout, the API SHALL reject them with 401.
> **Test**: `TestLoginHappyPath` — covers the first clause but not the second.

Score: ~60–70. Happy path covered; one scenario clause has no coverage. Note the gap explicitly.

### Low (~30%)

> **Scenario**: When session timeout exceeds 30 minutes, the API SHALL terminate the session.
> **Test**: `TestConcurrentSessions` — exercises concurrency, not timeout.

Score: ~20–30. Test name overlaps ("sessions") but the behaviour tested is different. Not a coverage gap; just unrelated.

### Orphaned test

> **Test**: `TestHelperLoadFixture` — pure test-utility helper, no behaviour assertion.
> **Match**: None — but not a gap; utility tests don't correspond to scenarios.

Score: 0. Flag as orphaned, not as gap. Suggest documenting as utility.

## Applying the rubric

For each scenario, score the best-matching test (if any). For each test, list the matching scenario (if any). The diff between the two sets is the gap.

**High** → no action needed.
**Medium** → note the partial coverage in the report.
**Low** → coverage gap; recommend a test that exercises the missing scenario.

## See also

- `references/semantic-extraction.md` — how to extract actions, entities, conditions, outcomes from specs and tests.
- `references/test-discovery-strategies.md` — finding the test files.