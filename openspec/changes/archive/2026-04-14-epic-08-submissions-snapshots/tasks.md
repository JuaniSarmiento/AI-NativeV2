## 1. Models + Migration

- [x] 1.1 Create `backend/app/features/submissions/models.py` with Submission, CodeSnapshot, ActivitySubmission models
- [x] 1.2 Create migration `backend/alembic/versions/008_submissions_snapshots.py`
- [x] 1.3 Update `backend/alembic/env.py` with new model imports

## 2. Schemas

- [x] 2.1 Create `backend/app/features/submissions/schemas.py` with SubmitActivityRequest, SubmissionResponse, ActivitySubmissionResponse, SnapshotRequest

## 3. Services

- [x] 3.1 Create `backend/app/features/submissions/services.py` with SubmissionService (submit activity, list student submissions, list all for docente) and SnapshotService (save snapshot, immutable)

## 4. Router

- [x] 4.1 Create `backend/app/features/submissions/router.py` with: POST submit activity, POST snapshot, GET student submissions, GET docente submissions
- [x] 4.2 Register submissions router in `backend/app/main.py`

## 5. Frontend — Auto-snapshot + Submit

- [x] 5.1 Create `frontend/src/features/submissions/useAutoSnapshot.ts` hook (30s interval, only if code changed, + before execution)
- [x] 5.2 Update `frontend/src/features/activities/StudentActivityViewPage.tsx` with auto-snapshot hook + "Enviar actividad" button with confirmation modal on last exercise
- [x] 5.3 Create `frontend/src/features/submissions/SubmissionHistoryPage.tsx` for student to see past attempts

## 6. App Integration

- [x] 6.1 Update `frontend/src/App.tsx` with submission history route

## 7. Tests

- [x] 7.1 Create `backend/tests/integration/test_submissions.py` with tests for submit activity, snapshots, student list, docente list, events
