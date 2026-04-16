## 1. Models + Migration

- [x] 1.1 Create `app/features/cognitive/__init__.py`
- [x] 1.2 Create CognitiveSession and CognitiveEvent models in schema cognitive
- [x] 1.3 Create Alembic migration 012 for both tables
- [x] 1.4 Register models in metadata

## 2. Cognitive Event Classifier

- [x] 2.1 Create classifier with event_type mapping
- [x] 2.2 Handle tutor.interaction.completed split by role
- [x] 2.3 Map all 9 raw event types to canonical cognitive event types

## 3. CTR Builder (Hash Chain)

- [x] 3.1 Create ctr_builder with hash computation functions
- [x] 3.2 Implement genesis_hash
- [x] 3.3 Implement event_hash chain
- [x] 3.4 Implement session_hash
- [x] 3.5 Implement verify_chain

## 4. Cognitive Service + Repository

- [x] 4.1 Create repositories (CognitiveSessionRepository, CognitiveEventRepository)
- [x] 4.2 Create CognitiveService
- [x] 4.3 Implement get_or_create_session
- [x] 4.4 Implement add_event with hash chain
- [x] 4.5 Implement close_session
- [x] 4.6 Implement verify_session
- [x] 4.7 Implement invalidate on hash failure

## 5. Event Bus Consumer

- [x] 5.1 Create CognitiveEventConsumer class
- [x] 5.2 Implement XREADGROUP for 3 streams
- [x] 5.3 Implement event processing pipeline
- [x] 5.4 Implement reconnection with backoff
- [x] 5.5 Register consumer in app lifespan

## 6. Session Timeout Worker

- [x] 6.1 Create timeout checker (every 5 min, close >30 min inactive)
- [x] 6.2 Register timeout worker in app lifespan

## 7. Cognitive API Endpoints

- [x] 7.1 Create schemas
- [x] 7.2 Create router with GET session + GET verify endpoints
- [x] 7.3 Register router in main.py

## 8. Tests

- [x] 8.1 Classifier tests (16 tests)
- [x] 8.2 CTR builder tests (18 tests — hash determinism, chain, tamper detection)
- [x] 8.3 Hash chain verification tests
- [x] 8.4 Session lifecycle tests
- [x] 8.5 CognitiveService tests (13 tests)
- [x] 8.6 Total: 47 tests passing
