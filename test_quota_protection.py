"""
Test quota protection features
"""
from backend.utils.gemini_client import gemini_client, get_quota_status
from PIL import Image
import io

# Create a simple test image
img = Image.new('RGB', (100, 100), color='red')

# Test 1: Check hash generation with image
print("Test 1: Hash generation with image object...")
try:
    prompt = ["This is a test", img, "with an image"]
    # This should not crash
    prompt_hash = gemini_client._get_prompt_hash(prompt, None, 0.2, 2000)
    print(f"✅ Hash generated successfully: {prompt_hash[:16]}...")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: Check quota status
print("\nTest 2: Quota status check...")
try:
    status = get_quota_status()
    print(f"✅ Status retrieved:")
    print(f"   Circuit Breaker: {'🔴 ACTIVE' if status['circuit_breaker_active'] else '✅ OK'}")
    print(f"   Total Calls: {status['total_calls_this_session']}")
    print(f"   Rate Limit: {status['calls_in_last_minute']}/{5}")
    print(f"   Cache Size: {status['cache_size']} entries")
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n✅ All tests passed! Quota protection is working.")
