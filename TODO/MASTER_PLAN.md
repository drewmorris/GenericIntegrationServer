# 🎯 MULTI-TENANT INTEGRATION SERVER - MASTER PLAN

**Date**: August 31, 2025  
**Status**: Phase 1 - Planning Complete, Ready for Implementation  
**Approach**: LegacyCode Extension + Component Salvage  

---

## 📋 EXECUTIVE SUMMARY

### What We're Building
A **multi-tenant integration server** that leverages Onyx's robust 40+ connector ecosystem to sync data to external destinations (initially CleverBrag) instead of internal indexing/RAG systems.

### Key Requirements
1. **Multi-tenancy**: Support multiple users/organizations with proper data isolation
2. **Destination routing**: Send connector data to CleverBrag instead of Onyx indexing
3. **UI management**: Allow users to configure connectors, destinations, and monitor sync status
4. **Robustness**: Maintain all existing Onyx connector reliability and error handling
5. **Testing**: Comprehensive unit and integration test coverage

---

## 🚨 LESSONS LEARNED - WHY OUR FIRST APPROACH FAILED

### The Failed "Extraction" Strategy (3+ weeks wasted)
**What we tried**: Extract connectors from Onyx and build a clean integration server from scratch
**Why it failed**: 
- ❌ **Underestimated dependencies**: Onyx connectors have deep integration with 100+ modules
- ❌ **Whack-a-mole errors**: Fixed ~3,000 mypy errors, only to introduce 2,400+ more
- ❌ **Bridge architecture complexity**: Created maintenance nightmare with 50+ bridge modules
- ❌ **Insufficient domain knowledge**: Made assumptions about "essential" vs "non-essential" components
- ❌ **Breaking working system**: Tried to surgically remove from tightly coupled architecture

### Key Technical Failures
1. **Import Hell**: Every connector imports 20-50 Onyx modules (db, utils, configs, etc.)
2. **Hidden Dependencies**: Components we thought were "search-only" were actually essential
3. **Type System Complexity**: mypy errors multiplied exponentially with each "fix"
4. **Connector Coupling**: Connectors deeply integrated with Onyx's orchestration system

### What We Learned
- ✅ **Don't fight the framework**: Work WITH existing systems, not against them
- ✅ **Proven foundations**: LegacyCode's 40+ connectors are battle-tested and robust
- ✅ **Component reuse**: We built valuable multi-tenant components that ARE salvageable
- ✅ **Extension over extraction**: Add functionality to existing systems rather than extracting

---

## 🎯 NEW APPROACH - LEGACYCODE EXTENSION + SALVAGE

### Core Strategy: "Embrace and Extend"
Instead of extracting connectors, we **extend LegacyCode** with multi-tenancy and destination routing while **salvaging our valuable components**.

### Architecture Decision
```
┌─────────────────────────────────────────────────────────────┐
│                  EXTENDED ONYX SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│  Multi-Tenant UI  │  Destination Config  │  Sync Monitoring │
├─────────────────────────────────────────────────────────────┤
│           Document Router (NEW - Salvaged)                   │
│    ┌─────────────────────┐       ┌──────────────────────┐    │
│    │   40+ Connectors    │──────▶│  CleverBrag Client   │    │
│    │   (LegacyCode)      │       │   (Salvaged)        │    │
│    │   - Gmail           │       └──────────────────────┘    │
│    │   - Google Drive    │                                   │
│    │   - Slack           │       ┌──────────────────────┐    │
│    │   - Salesforce      │       │   Vespa Indexing    │    │
│    │   - etc...          │──────▶│   (DISABLED)        │    │
│    └─────────────────────┘       └──────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│     Multi-Tenant Database Layer (NEW - Salvaged)            │
│  Organizations │ DestinationTargets │ Enhanced CC-Pairs     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 SALVAGEABLE COMPONENTS (70-80% of work saved!)

### ✅ FULLY REUSABLE (90%+ - 2+ weeks saved)
1. **CleverBrag Integration** (`backend/destinations/cleverbrag.py`)
   - Complete R2R API client implementation
   - Per-user base_url + api_key configuration
   - Error handling, retries, batch processing
   - Test mode support for development

2. **Multi-Tenant Database Schema** (`backend/db/models.py`)
   - DestinationTarget model with proper tenant isolation
   - Enhanced ConnectorCredentialPair with destination routing
   - Unique constraints and foreign key relationships
   - Clean organization_id + user_id separation

3. **Database Migrations** (`backend/db/migrations/versions/`)
   - Non-breaking schema additions
   - Proper indexing for performance
   - Clean rollback strategies

4. **Pydantic Schemas** (`backend/schemas/`)
   - DestinationTarget CRUD operations
   - Enhanced CC-Pair schemas with multi-tenancy
   - Clean API contracts with validation

### ✅ MODERATELY REUSABLE (60-70% - 1 week saved)
1. **Destination Framework** (`backend/destinations/base.py`)
   - Abstract DestinationBase class
   - Registry and lazy loading patterns
   - Health checking and metrics
   - *Needs*: Integration with LegacyCode pipeline

2. **Multi-Tenant Middleware** (`backend/auth/`)
   - JWT token parsing for tenant context
   - Request isolation patterns
   - *Needs*: Integration with LegacyCode auth

---

## 🗓️ DETAILED IMPLEMENTATION PHASES

### **PHASE 1: Database Foundation (Week 1 - 5 days)**

#### Day 1-2: Schema Migration to LegacyCode
```bash
# Tasks:
1. Copy DestinationTarget model to LegacyCode/backend/onyx/db/models.py
2. Add organization_id to existing ConnectorCredentialPair 
3. Add destination_target_id to existing ConnectorCredentialPair
4. Create migration script for LegacyCode alembic system
5. Test migration on development database

# Files to modify:
- LegacyCode/backend/onyx/db/models.py
- LegacyCode/backend/alembic/versions/[new_migration].py

# Acceptance criteria:
- ✅ All existing data preserved during migration
- ✅ New columns added with proper constraints
- ✅ Foreign key relationships established
- ✅ Database tests pass
```

#### Day 3-4: Enhanced Models and Relationships  
```python
# Add to LegacyCode models.py:
class DestinationTarget(Base):
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))  # Use existing User table
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)  # "cleverbrag" 
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(postgresql.JSONB(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Enhance existing ConnectorCredentialPair:
class ConnectorCredentialPair(Base):
    # Add new fields:
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    destination_target_id: Mapped[UUID | None] = mapped_column(ForeignKey("destinationtarget.id"), nullable=True)
    
    # Add relationships:
    destination_target: Mapped["DestinationTarget"] = relationship("DestinationTarget")
```

#### Day 5: API Schema Integration
```python
# Copy and adapt our Pydantic schemas to LegacyCode:
# LegacyCode/backend/onyx/server/manage/destination_models.py

class DestinationTargetCreate(BaseModel):
    name: str = Field(..., examples=["cleverbrag"])
    display_name: str = Field(..., examples=["CleverBrag Production"])  
    config: dict[str, Any] = Field(default_factory=dict)

class DestinationTargetOut(DestinationTargetCreate):
    id: UUID
    user_id: UUID
    created_at: datetime
```

### **PHASE 2: Destination System Integration (Week 1.5 - 3 days)**

#### Day 1: Port Destination Framework
```bash
# Copy our destination system to LegacyCode:
cp -r backend/destinations/ → LegacyCode/backend/onyx/destinations/

# Modify imports to work with LegacyCode structure:
# - Update all imports from "backend.*" to "onyx.*"  
# - Integrate with LegacyCode's logging system
# - Connect with LegacyCode's configuration management
```

#### Day 2-3: CleverBrag Client Integration
```python
# Adapt our CleverBragDestination for LegacyCode:
# LegacyCode/backend/onyx/destinations/cleverbrag.py

@register("cleverbrag")
class CleverBragDestination(DestinationBase):
    async def send(self, payload: Iterable[Document], destination_config: dict):
        base_url = destination_config["base_url"]  # From DestinationTarget.config
        api_key = destination_config["api_key"]
        
        # Convert Onyx Document format → R2R format
        r2r_documents = [self._convert_onyx_to_r2r(doc) for doc in payload]
        
        # Post to CleverBrag /v3/documents endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v3/documents",
                headers={"X-API-Key": api_key},
                json=r2r_documents
            )
            response.raise_for_status()
```

### **PHASE 3: Connector Pipeline Integration (Week 2 - 5 days)**

#### Day 1-2: Identify Integration Points
```python
# Research LegacyCode connector pipeline:
# Find where documents are processed after connector extraction
# Likely locations:
# - LegacyCode/backend/onyx/connectors/connector_runner.py
# - LegacyCode/backend/onyx/document_index/
# - LegacyCode/backend/onyx/background/celery/tasks/

# Goal: Find the function that receives documents from connectors
# and routes them to indexing - this is where we intercept
```

#### Day 3-4: Document Router Implementation
```python
# Create new document router:
# LegacyCode/backend/onyx/destinations/router.py

async def route_documents(
    cc_pair_id: int, 
    documents: List[Document],
    db_session: Session
) -> None:
    """Route documents to destination or continue with Onyx indexing"""
    
    # Get CC-Pair with destination info
    cc_pair = await get_cc_pair_with_destination(cc_pair_id, db_session)
    
    if cc_pair.destination_target_id:
        # Route to external destination
        destination_target = await get_destination_target(cc_pair.destination_target_id)
        destination_client = get_destination(destination_target.name)  # "cleverbrag"
        
        await destination_client.send(
            payload=documents,
            destination_config=destination_target.config
        )
        
        # Log successful routing
        logger.info(f"Routed {len(documents)} documents to {destination_target.name}")
        return
    
    # No destination configured - skip processing (no Onyx indexing needed)
    logger.info(f"No destination configured for CC-Pair {cc_pair_id}, skipping documents")
```

#### Day 5: Pipeline Modification
```python
# Modify existing LegacyCode connector pipeline:
# Replace calls to document indexing with calls to our router

# BEFORE (in LegacyCode):
def process_connector_documents(cc_pair_id: int, documents: List[Document]):
    # ... existing connector logic ...
    send_to_vespa_indexing(documents)  # OLD

# AFTER (modified):
def process_connector_documents(cc_pair_id: int, documents: List[Document]):
    # ... existing connector logic ...
    await route_documents(cc_pair_id, documents, db_session)  # NEW
```

### **PHASE 4: API Endpoints (Week 2.5 - 2 days)**

#### Day 1: Destination Management APIs
```python
# Add to LegacyCode API routes:
# LegacyCode/backend/onyx/server/manage/destination_routes.py

@router.post("/destinations", response_model=DestinationTargetOut)
async def create_destination(
    destination: DestinationTargetCreate,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_session)
):
    """Create a new destination target for the current user"""
    
    destination_target = DestinationTarget(
        user_id=current_user.id,
        organization_id=current_user.id,  # Simple: user_id = org_id initially
        name=destination.name,
        display_name=destination.display_name,
        config=destination.config
    )
    
    db_session.add(destination_target)
    db_session.commit()
    return destination_target

@router.get("/destinations", response_model=List[DestinationTargetOut])
async def list_destinations(
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_session)
):
    """List all destination targets for the current user"""
    return db_session.query(DestinationTarget).filter(
        DestinationTarget.user_id == current_user.id
    ).all()
```

#### Day 2: Enhanced CC-Pair APIs
```python
# Modify existing CC-Pair endpoints to support destination assignment:
# LegacyCode/backend/onyx/server/manage/connector_routes.py

class ConnectorCredentialPairCreate(BaseModel):
    # ... existing fields ...
    destination_target_id: Optional[UUID] = None  # NEW

@router.post("/connector-credential-pairs")
async def create_cc_pair(
    cc_pair_data: ConnectorCredentialPairCreate,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_session)
):
    # Validate destination belongs to user
    if cc_pair_data.destination_target_id:
        destination = db_session.query(DestinationTarget).filter(
            DestinationTarget.id == cc_pair_data.destination_target_id,
            DestinationTarget.user_id == current_user.id
        ).first()
        if not destination:
            raise HTTPException(400, "Invalid destination target")
    
    # Create CC-Pair with destination link
    cc_pair = ConnectorCredentialPair(
        # ... existing fields ...
        destination_target_id=cc_pair_data.destination_target_id,
        organization_id=current_user.id
    )
    # ... rest of creation logic ...
```

### **PHASE 5: UI Modifications (Week 3 - 5 days)**

#### Day 1-2: Destination Management UI
```typescript
// Add to LegacyCode React frontend:
// LegacyCode/web/src/app/admin/destinations/page.tsx

export default function DestinationsPage() {
  const [destinations, setDestinations] = useState<DestinationTarget[]>([]);

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-2xl font-bold mb-6">Destination Targets</h1>
      
      <div className="grid gap-6">
        {/* CleverBrag Configuration Card */}
        <Card>
          <CardHeader>
            <CardTitle>CleverBrag Configuration</CardTitle>
            <CardDescription>Configure your CleverBrag instance for document syncing</CardDescription>
          </CardHeader>
          <CardContent>
            <DestinationForm 
              destinationType="cleverbrag"
              onSubmit={(config) => createDestination("cleverbrag", config)}
            />
          </CardContent>
        </Card>

        {/* Existing Destinations */}
        <Card>
          <CardHeader>
            <CardTitle>Your Destinations</CardTitle>
          </CardHeader>
          <CardContent>
            <DestinationsList destinations={destinations} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

#### Day 3-4: Enhanced Connector Setup
```typescript
// Modify existing connector setup to include destination selection:
// LegacyCode/web/src/components/admin/connectors/ConnectorForm.tsx

export function ConnectorForm({ connector, onSubmit }: ConnectorFormProps) {
  const [selectedDestination, setSelectedDestination] = useState<string | null>(null);
  const { data: destinations } = useDestinations();

  return (
    <form onSubmit={handleSubmit}>
      {/* Existing connector configuration fields */}
      <ConnectorConfigFields connector={connector} />
      
      {/* NEW: Destination Selection */}
      <FormField
        control={form.control}
        name="destination_target_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Sync Destination</FormLabel>
            <Select onValueChange={field.onChange} defaultValue={field.value}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue placeholder="Select where to sync documents" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {destinations?.map((dest) => (
                  <SelectItem key={dest.id} value={dest.id}>
                    {dest.display_name} ({dest.name})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormDescription>
              Choose which destination to sync documents to, or leave blank to skip syncing.
            </FormDescription>
          </FormItem>
        )}
      />
      
      <Button type="submit">Create Connector</Button>
    </form>
  );
}
```

#### Day 5: Sync Status Monitoring
```typescript
// Add sync status monitoring:
// LegacyCode/web/src/app/admin/sync-status/page.tsx

export default function SyncStatusPage() {
  const { data: ccPairs } = useConnectorCredentialPairs();
  const { data: syncMetrics } = useSyncMetrics();

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-2xl font-bold mb-6">Sync Status</h1>
      
      <div className="grid gap-4">
        {ccPairs?.map((ccPair) => (
          <Card key={ccPair.id}>
            <CardHeader>
              <CardTitle>{ccPair.name}</CardTitle>
              <CardDescription>
                {ccPair.destination_target 
                  ? `Syncing to: ${ccPair.destination_target.display_name}`
                  : "No destination configured"
                }
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SyncStatusIndicator 
                ccPairId={ccPair.id}
                lastSyncTime={ccPair.last_successful_index_time}
                syncMetrics={syncMetrics[ccPair.id]}
              />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

### **PHASE 6: Testing & Quality Assurance (Week 3.5 - 2 days)**

#### Day 1: Unit Testing
```python
# Test Coverage Required:
1. DestinationTarget CRUD operations
2. CleverBragDestination API integration
3. Document routing logic
4. Multi-tenant data isolation
5. Error handling and retries

# Example test:
# tests/unit/destinations/test_cleverbrag.py
class TestCleverBragDestination:
    async def test_send_documents_success(self):
        destination = CleverBragDestination()
        mock_config = {
            "base_url": "https://test.cleverbrag.com",
            "api_key": "test-key"
        }
        documents = [create_test_document()]
        
        with mock_httpx_client() as mock_client:
            await destination.send(payload=documents, destination_config=mock_config)
            
            # Verify API call
            assert mock_client.post.called
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://test.cleverbrag.com/v3/documents"
            assert call_args[1]["headers"]["X-API-Key"] == "test-key"
```

#### Day 2: Integration Testing
```python
# Integration tests:
# tests/integration/test_end_to_end_sync.py
class TestEndToEndSync:
    async def test_gmail_to_cleverbrag_sync(self):
        """Test complete flow: Gmail connector → Document router → CleverBrag"""
        
        # Setup test user and destination
        user = create_test_user()
        destination = create_test_destination_target(
            user_id=user.id,
            name="cleverbrag",
            config={"base_url": "https://test.cleverbrag.com", "api_key": "test"}
        )
        
        # Setup Gmail connector with destination
        cc_pair = create_test_cc_pair(
            connector_type="gmail",
            user_id=user.id,
            destination_target_id=destination.id
        )
        
        # Mock Gmail API responses
        with mock_gmail_api(), mock_cleverbrag_api():
            # Trigger connector run
            await run_connector(cc_pair.id)
            
            # Verify documents were sent to CleverBrag
            assert cleverbrag_received_documents()
            assert not vespa_received_documents()  # Verify indexing was bypassed
```

---

## 🎯 SUCCESS CRITERIA

### Must-Have Features
- ✅ **Multi-tenant isolation**: Users can only see/manage their own connectors and destinations
- ✅ **CleverBrag integration**: Documents successfully sync to user-configured CleverBrag instances  
- ✅ **UI workflow**: Complete user flow from connector setup → destination config → sync monitoring
- ✅ **Data integrity**: Zero data loss during connector operations
- ✅ **Error handling**: Graceful handling of destination failures with retry logic

### Performance Targets  
- ✅ **Sync latency**: Documents appear in CleverBrag within 5 minutes of source update
- ✅ **Throughput**: Handle 1000+ documents per connector run without issues
- ✅ **UI responsiveness**: All pages load within 2 seconds
- ✅ **Database performance**: Multi-tenant queries complete within 100ms

### Quality Gates
- ✅ **Test coverage**: 90%+ code coverage for new components
- ✅ **Integration tests**: End-to-end tests for each connector type
- ✅ **Error monitoring**: Comprehensive logging and alerting
- ✅ **Documentation**: Complete API documentation and user guides

---

## 🚨 RISK MITIGATION

### Technical Risks
1. **LegacyCode integration complexity**
   - *Risk*: LegacyCode codebase may be difficult to modify
   - *Mitigation*: Thorough code analysis in Phase 3 before making changes

2. **Data migration issues**
   - *Risk*: Existing Onyx data could be corrupted during schema changes
   - *Mitigation*: Comprehensive backup strategy and rollback plan

3. **Performance degradation**
   - *Risk*: Adding destination routing could slow down connector operations
   - *Mitigation*: Asynchronous processing and performance monitoring

### Project Risks
1. **Timeline compression**
   - *Risk*: 2.5 week timeline may be aggressive
   - *Mitigation*: Phase-based delivery, can ship basic functionality early

2. **Scope creep**
   - *Risk*: Additional destination types or features requested mid-project
   - *Mitigation*: Clear scope definition, change request process

---

## 📊 TIMELINE SUMMARY

| Phase | Duration | Key Deliverables | Success Metrics |
|-------|----------|------------------|-----------------|
| **Phase 1** | 5 days | Database schema, migrations | ✅ Schema deployed, tests pass |
| **Phase 2** | 3 days | Destination framework | ✅ CleverBrag client working |  
| **Phase 3** | 5 days | Pipeline integration | ✅ Documents route to destination |
| **Phase 4** | 2 days | API endpoints | ✅ CRUD operations working |
| **Phase 5** | 5 days | UI modifications | ✅ Complete user workflow |
| **Phase 6** | 2 days | Testing & QA | ✅ 90% test coverage |

**Total: 22 days (~4.5 weeks with buffer)**

---

## 🏁 GETTING STARTED

### Immediate Next Steps (Today)
1. ✅ **Create this plan** - Document complete approach
2. 🎯 **Environment setup** - Ensure LegacyCode is running locally  
3. 📋 **Code analysis** - Study LegacyCode connector pipeline architecture
4. 🗃️ **Component preparation** - Prepare our salvageable components for porting

### Week 1 Kickoff Tasks
1. **Database schema analysis** - Map our schema to LegacyCode models
2. **Migration script creation** - Write Alembic migration for LegacyCode
3. **Development environment** - Set up development workflow
4. **Team alignment** - Review plan with stakeholders

---

**This plan represents our pivot from "extraction failure" to "extension success" - leveraging both the proven LegacyCode foundation and our valuable salvaged components for a robust, multi-tenant integration server.**
