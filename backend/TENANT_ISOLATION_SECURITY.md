# Tenant Isolation Security System

## 🛡️ **Threat Model**

This system defends against the following attack vectors in a multi-tenant SaaS application:

### **Primary Threats**

1. **Malicious Authenticated Users**
   - Users attempting to access data from other churches
   - Privilege escalation attempts through tenant manipulation
   - API parameter tampering to bypass tenant boundaries

2. **Accidental Data Leakage**
   - Developers forgetting to filter queries by tenant
   - Missing tenant checks in new API endpoints
   - Cross-tenant data exposure through incomplete filters

3. **Insider Threats**
   - Staff/superuser accounts attempting unauthorized cross-tenant access
   - Administrative operations that bypass tenant boundaries
   - Accidental bulk operations affecting multiple tenants

4. **API Security Bypasses**
   - Direct object reference attacks across tenants
   - Missing authorization checks on tenant-scoped resources
   - Inconsistent tenant enforcement across endpoints

### **Security Principles**

- **Fail Securely**: Unknown/missing tenant context results in explicit denial
- **No Silent Failures**: All violations logged and blocked with clear error messages
- **No Superuser Bypass**: Even administrators must respect tenant boundaries
- **Default Deny**: Requires explicit tenant access grants
- **Defense in Depth**: Multiple layers of tenant isolation enforcement

---

## 🔧 **Implementation Components**

### **1. Tenant Context Middleware**
```python
# File: core/tenant_isolation.py
class TenantContextMiddleware
```

**Purpose**: Injects tenant context into every authenticated API request

**Security Features**:
- Sets `request.church` from authenticated user
- Blocks users without church assignment
- Logs all tenant context for audit trail
- Runs after authentication middleware

**Failure Modes**:
- Returns 403 for users without church assignment
- Logs security violations for monitoring

### **2. Tenant Isolation Permissions**
```python
# File: core/tenant_isolation.py
class TenantIsolationPermission
class SuperuserBypassDenied
```

**Purpose**: Enforces tenant boundaries at the view level

**Security Features**:
- Requires authenticated users with church assignment
- Validates tenant context on every request
- Prevents cross-tenant object access
- Blocks superuser bypass attempts

**Object-Level Security**:
```python
def has_object_permission(self, request, view, obj):
    # Ensures obj.church == request.church
```

### **3. Tenant-Scoped QuerySets**
```python
# File: core/tenant_isolation.py
class TenantScopedQuerySetMixin
def get_tenant_object_or_404()
```

**Purpose**: Automatic tenant filtering for database queries

**Security Features**:
- All queries automatically filtered by `request.church`
- Prevents accidental cross-tenant data exposure
- Secure object retrieval with tenant validation

### **4. Tenant-Aware Base Views**
```python
# File: core/tenant_views.py
class TenantViewMixin
class TenantModelViewSet
```

**Purpose**: Pre-built view classes with tenant isolation

**Security Features**:
- Automatic queryset filtering by church
- Church assignment on object creation
- Prevents church reassignment via updates
- Comprehensive audit logging

---

## 📝 **Usage Examples**

### **Secure Model Definition**
```python
from core.tenant_isolation import TenantScopedQuerySetMixin
from tenants.models import Church

class Photo(TenantScopedQuerySetMixin, models.Model):
    # REQUIRED: Every tenant model must have church field
    church = models.ForeignKey(Church, on_delete=models.CASCADE)
    
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='photos/')
    uploaded_by = models.ForeignKey('core.User', on_delete=models.CASCADE)
    
    class Meta:
        # Optimize tenant-scoped queries
        indexes = [models.Index(fields=['church', 'created_at'])]
        # Prevent duplicates within tenant
        unique_together = [['church', 'title']]
```

### **Secure ViewSet Implementation**
```python
from core.tenant_views import TenantModelViewSet

class PhotoViewSet(TenantModelViewSet):
    model = Photo
    serializer_class = PhotoSerializer
    
    # Automatic tenant isolation - no additional code required
    # - get_queryset() filtered by request.church
    # - perform_create() assigns request.church
    # - Cross-tenant access automatically blocked
```

### **Function-Based View Security**
```python
from core.tenant_isolation import enforce_tenant_isolation, get_tenant_object_or_404

@enforce_tenant_isolation
def photo_detail(request, photo_id):
    # Guaranteed tenant-scoped access
    photo = get_tenant_object_or_404(Photo, request, id=photo_id)
    
    return JsonResponse({
        'title': photo.title,
        'church': photo.church.name,  # Always matches request.church
        'secure': True
    })
```

### **Safe Object Retrieval**
```python
# ❌ INSECURE - Could access any tenant's data
photo = Photo.objects.get(id=photo_id)

# ✅ SECURE - Automatically tenant-scoped
photo = get_tenant_object_or_404(Photo, request, id=photo_id)

# ✅ SECURE - Using model mixin
photos = Photo.get_tenant_scoped_queryset(request)
```

---

## 🚨 **Security Testing**

### **Attack Simulation Tests**
```python
def test_cross_tenant_access_blocked():
    # User from Church A attempts to access Church B's data
    church_a_user = create_test_user(church=church_a)
    church_b_photo = create_test_photo(church=church_b)
    
    client.force_authenticate(user=church_a_user)
    response = client.get(f'/api/photos/{church_b_photo.id}/')
    
    # Should return 404, not 403 (don't reveal existence)
    assert response.status_code == 404

def test_superuser_bypass_denied():
    superuser = create_superuser()
    church_photo = create_test_photo(church=some_church)
    
    client.force_authenticate(user=superuser)
    response = client.get(f'/api/photos/{church_photo.id}/')
    
    # Even superusers cannot bypass tenant boundaries
    assert response.status_code == 403
    assert 'tenant' in response.data['message'].lower()
```

### **Data Leakage Prevention**
```python
def test_no_cross_tenant_data_in_lists():
    church_a_user = create_test_user(church=church_a)
    create_test_photo(church=church_a, title="Church A Photo")
    create_test_photo(church=church_b, title="Church B Photo") 
    
    client.force_authenticate(user=church_a_user)
    response = client.get('/api/photos/')
    
    # Should only see Church A's photos
    titles = [photo['title'] for photo in response.data['results']]
    assert "Church A Photo" in titles
    assert "Church B Photo" not in titles
```

---

## 🔍 **Monitoring & Alerts**

### **Security Event Logging**
All tenant isolation events are logged with structured data:

```python
# Successful tenant access
logger.info("Tenant access: user=user@church.com, church=First Baptist, path=/api/photos/, method=GET")

# Security violations  
logger.warning("SECURITY: Cross-tenant access attempt by user@church.com (church: First Baptist) to Photo belonging to Second Baptist")

# Missing tenant context
logger.error("SECURITY: Missing tenant context for user@church.com on /api/photos/ - middleware may not be configured")
```

### **Recommended Alerts**
- Any log message containing "SECURITY:"
- Users accessing APIs without church assignment
- Multiple cross-tenant access attempts from same user
- Superuser bypass attempts
- Missing tenant context errors

---

## ⚡ **Performance Considerations**

### **Database Optimization**
```python
class Photo(models.Model):
    church = models.ForeignKey(Church, on_delete=models.CASCADE)
    # ... other fields
    
    class Meta:
        # CRITICAL: Index on church for fast filtering
        indexes = [
            models.Index(fields=['church']),
            models.Index(fields=['church', 'created_at']),  # For time-based queries
        ]
```

### **Query Efficiency**
```python
# ✅ Efficient - Single query with church filter
photos = Photo.objects.filter(church=request.church).select_related('uploaded_by')

# ❌ Inefficient - N+1 queries checking church per object
for photo in Photo.objects.all():
    if photo.church == request.church:  # This creates N+1 queries
        process_photo(photo)
```

---

## 🔒 **Deployment Checklist**

### **Before Production**
- [ ] `TenantContextMiddleware` added to `MIDDLEWARE` after authentication
- [ ] All tenant models inherit from `TenantScopedQuerySetMixin`
- [ ] All tenant models have `church` field with proper index
- [ ] All API views use `TenantViewMixin` or equivalent permissions
- [ ] Security logging configured and monitored
- [ ] Cross-tenant access tests pass
- [ ] Superuser bypass tests pass

### **Production Monitoring**
- [ ] Security event alerting configured
- [ ] Log aggregation for tenant violations
- [ ] Performance monitoring for church-filtered queries
- [ ] Regular security audit of new endpoints

---

## 🚀 **Integration with Existing Code**

### **Minimal Migration Path**
1. Add middleware to settings
2. Update existing models to inherit from `TenantScopedQuerySetMixin`
3. Replace existing ViewSets with `TenantModelViewSet`
4. Add security tests
5. Deploy with monitoring

### **Gradual Rollout**
- Start with new endpoints using tenant-aware base classes
- Migrate existing endpoints one by one
- Use feature flags to enable tenant isolation per endpoint
- Monitor for any performance or functionality regressions

The tenant isolation system provides **defense-in-depth security** while maintaining developer productivity through easy-to-use base classes and automatic enforcement.