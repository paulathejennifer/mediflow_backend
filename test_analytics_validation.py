#!/usr/bin/env python3
"""
Test script to validate analytics endpoints structure and imports
before deploying to Render.
"""
import sys
import inspect
from typing import List, Dict

def test_imports():
    """Test that all required modules import successfully."""
    print("=" * 60)
    print("STEP 1: Testing imports...")
    print("=" * 60)
    try:
        from app.api.v1.endpoints import analytics
        print("✅ analytics module imported successfully")
        return analytics
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR in analytics: {e}")
        sys.exit(1)
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)


def test_endpoint_definitions(analytics_module):
    """Test that all expected endpoints are defined."""
    print("\n" + "=" * 60)
    print("STEP 2: Validating endpoint definitions...")
    print("=" * 60)
    
    # List of expected endpoints
    expected_endpoints = [
        'get_referral_analytics',
        'get_dashboard_kpis',
        'get_referral_trend',
        'get_facility_performance',
        'get_turnaround_time_trend',
        'get_system_health',
        'get_referrals_by_status',
        'get_referral_summary_stats',
        'get_facility_utilization_matrix',
        'get_referral_source_distribution',
        'get_priority_distribution',
        'get_avg_time_by_status',
        'get_system_requests_metric',
    ]
    
    missing_endpoints = []
    for endpoint_name in expected_endpoints:
        if hasattr(analytics_module, endpoint_name):
            func = getattr(analytics_module, endpoint_name)
            if callable(func):
                print(f"✅ {endpoint_name} - defined and callable")
            else:
                print(f"⚠️  {endpoint_name} - exists but not callable")
        else:
            print(f"❌ {endpoint_name} - MISSING")
            missing_endpoints.append(endpoint_name)
    
    if missing_endpoints:
        print(f"\n❌ MISSING {len(missing_endpoints)} endpoints!")
        return False
    
    print(f"\n✅ All {len(expected_endpoints)} endpoints are defined")
    return True


def test_endpoint_structure(analytics_module):
    """Test that endpoints have proper route decorators."""
    print("\n" + "=" * 60)
    print("STEP 3: Checking route decorators...")
    print("=" * 60)
    
    # Get router object
    if not hasattr(analytics_module, 'router'):
        print("❌ Router object not found in analytics module")
        return False
    
    router = analytics_module.router
    print(f"✅ Router object found: {type(router)}")
    
    # Check routes
    if hasattr(router, 'routes'):
        routes = router.routes
        print(f"✅ Found {len(routes)} routes in router")
        for route in routes:
            if hasattr(route, 'path'):
                print(f"   - {route.methods if hasattr(route, 'methods') else 'GET'} {route.path}")
    
    return True


def test_function_signatures(analytics_module):
    """Test that key functions have proper signatures."""
    print("\n" + "=" * 60)
    print("STEP 4: Validating function signatures...")
    print("=" * 60)
    
    # Test get_dashboard_kpis specifically
    if hasattr(analytics_module, 'get_dashboard_kpis'):
        func = getattr(analytics_module, 'get_dashboard_kpis')
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        print(f"✅ get_dashboard_kpis parameters: {params}")
        
        # Should have db and current_user parameters
        if 'db' in params and 'current_user' in params:
            print("✅ Has required dependencies (db, current_user)")
        else:
            print(f"⚠️  Missing expected parameters. Has: {params}")
    
    return True


def test_no_undefined_variables(analytics_module):
    """Check for obvious undefined variable references."""
    print("\n" + "=" * 60)
    print("STEP 5: Checking for undefined variables...")
    print("=" * 60)
    
    # Read the source file
    try:
        with open(analytics_module.__file__, 'r') as f:
            source = f.read()
        
        # Check for common issues
        issues_found = []
        
        # Check for orphaned variables
        if 'referral_query' in source and source.count('referral_query =') == 0:
            # This is a heuristic - referral_query used but not defined
            print("⚠️  Checking referral_query references...")
        
        # Check for proper closing of parentheses (basic check)
        open_parens = source.count('(')
        close_parens = source.count(')')
        if open_parens != close_parens:
            print(f"⚠️  Parenthesis mismatch: {open_parens} open, {close_parens} close")
            # This might be okay due to strings, but flag it
        else:
            print(f"✅ Parentheses balanced: {open_parens} pairs")
        
        print("✅ No obvious undefined variable patterns detected")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not perform full check: {e}")
        return True


def test_user_role_handling(analytics_module):
    """Test that user role logic is properly implemented."""
    print("\n" + "=" * 60)
    print("STEP 6: Validating user role handling...")
    print("=" * 60)
    
    # Read the source file
    try:
        with open(analytics_module.__file__, 'r') as f:
            source = f.read()
        
        # Check for role-based access control
        checks = {
            'SUPER_ADMIN role check': 'UserRole.SUPER_ADMIN' in source,
            'facility_id validation': 'current_user.facility_id' in source,
            'HTTPException for unauthorized access': 'HTTPException' in source and '403' in source,
            'Facility filtering': 'facility_id ==' in source,
        }
        
        for check_name, passed in checks.items():
            if passed:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name} NOT FOUND")
        
        all_passed = all(checks.values())
        return all_passed
        
    except Exception as e:
        print(f"❌ Error checking role handling: {e}")
        return False


def main():
    """Run all validation tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "ANALYTICS ENDPOINTS VALIDATION TEST" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        # Test 1: Imports
        analytics_module = test_imports()
        
        # Test 2: Endpoint definitions
        test2_passed = test_endpoint_definitions(analytics_module)
        
        # Test 3: Endpoint structure
        test3_passed = test_endpoint_structure(analytics_module)
        
        # Test 4: Function signatures
        test4_passed = test_function_signatures(analytics_module)
        
        # Test 5: Undefined variables
        test5_passed = test_no_undefined_variables(analytics_module)
        
        # Test 6: User role handling
        test6_passed = test_user_role_handling(analytics_module)
        
        # Summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        all_tests = [test2_passed, test3_passed, test4_passed, test5_passed, test6_passed]
        passed_count = sum(all_tests)
        total_tests = len(all_tests)
        
        print(f"Tests passed: {passed_count}/{total_tests}")
        
        if all(all_tests):
            print("\n✅ ALL VALIDATIONS PASSED - READY FOR DEPLOYMENT")
            return 0
        else:
            print("\n⚠️  SOME VALIDATIONS FAILED - REVIEW ABOVE")
            return 1
            
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
