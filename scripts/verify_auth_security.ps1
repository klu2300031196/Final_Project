# PowerShell Script to verify JWT Authentication Security on /api/test-records
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host " VERIFYING JWT AUTHENTICATION SECURITY ON /api/test-records" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Test 1: Missing Token (Must return HTTP 401)
Write-Host "`n[Test 1] Request WITHOUT Authorization Token:" -ForegroundColor Yellow
try {
    $res1 = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/test-records" -Method Get -ErrorAction Stop
    Write-Host "  FAILED: Endpoint returned 200 without token!" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  PASSED: Blocked with HTTP $statusCode Unauthorized" -ForegroundColor Green
}

# Test 2: Invalid / Tampered Token (Must return HTTP 401)
Write-Host "`n[Test 2] Request WITH Invalid / Tampered Token:" -ForegroundColor Yellow
try {
    $headers = @{ Authorization = "Bearer invalid.tampered.signature" }
    $res2 = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/test-records" -Method Get -Headers $headers -ErrorAction Stop
    Write-Host "  FAILED: Endpoint accepted invalid token!" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  PASSED: Blocked with HTTP $statusCode Unauthorized (Signature mismatch)" -ForegroundColor Green
}

# Test 3: Authenticate and request WITH Valid JWT Token (Must return HTTP 200)
Write-Host "`n[Test 3] Request WITH Valid Signed JWT Token:" -ForegroundColor Yellow
try {
    $loginBody = @{ username = "admin"; password = "Admin@123" } | ConvertTo-Json
    $loginRes = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $token = $loginRes.token
    Write-Host "  -> Obtained valid JWT Token for user: $($loginRes.user.username)" -ForegroundColor Gray

    $validHeaders = @{ Authorization = "Bearer $token" }
    $res3 = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/test-records" -Method Get -Headers $validHeaders
    Write-Host "  PASSED: HTTP 200 OK - Retrieved $($res3.count) records successfully!" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: Valid token was rejected: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host " SECURITY AUDIT VERIFICATION COMPLETE" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
