# API timeout

Record the endpoint, HTTP method, status code, request ID, region, and UTC
timestamp. Retry transient timeouts with exponential backoff and jitter, while
respecting idempotency for write operations. Reduce unusually large request
payloads and confirm the client timeout is appropriate for the endpoint.

Do not retry indefinitely. Escalate repeated timeouts with sanitized request
metadata; never include secrets, authorization headers, or personal data in
logs or support messages.
