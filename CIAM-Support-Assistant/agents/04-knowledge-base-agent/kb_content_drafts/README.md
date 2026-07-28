# KB Content Drafts

Best-effort draft content for the 8 KB documents described in
`../KB_CONTENT_REQUIREMENTS.md`, built from everything established this
session (agent schemas, test scenarios, spec provisions) since no real
source material (Confluence exports, Jira TQI data, Auth0 tenant
scripts) was available.

**Every file here is explicitly marked DRAFT and lists its own open
questions.** None of this has been uploaded to the live S3 data source
(`s3://ciam-agent4-kb-docs-786063285476-us-east-1/docs/`) or synced into
the Bedrock Knowledge Base — the live KB still has the original 8
placeholder stubs. These drafts exist to give a concrete starting point
to correct against, not to be treated as verified truth.

## Two Documents Are NOT Usable As-Is

- `migration-known-issues.md` — contains no actual confirmed migration
  bugs, only a template + context.
- `resolved-tickets-patterns.md` — contains no real resolved tickets,
  only a template + anonymized test scenarios from this session (NOT
  real Jira data).

These two need real source data before they're worth uploading at all;
the other 6 are closer to a usable first draft, pending review.

## Next Steps

1. Review each draft against real source material (owners listed per-doc
   in `../KB_CONTENT_REQUIREMENTS.md`).
2. Once corrected, upload to
   `s3://ciam-agent4-kb-docs-786063285476-us-east-1/docs/` (replacing
   the placeholder stubs).
3. Trigger a data source sync in the Bedrock console (or via
   `bedrock-agent start-ingestion-job`).
4. Re-verify `derive_persona()` in `agent.py` against the corrected
   `birthright-entitlement-matrix.md` and `KNOWN_PORTAL_KEYWORDS`
   against the corrected `portal-access-requirements.md`.
