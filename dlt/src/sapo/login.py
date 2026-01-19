"""
Custom login strategy for Sapo source.
Handles Sapo-specific login quirks like disabled submit buttons and lazy validation.
"""
import time

def sapo_login_strategy(page, username, password, selectors):
    """
    Custom strategy to log in to Sapo.
    
    Args:
        page: Playwright Page object
        username: login username
        password: login password
        selectors: dict of selectors
    """
    print("   🚀 Executing Sapo Login Strategy")
    
    # Wait for username field
    page.wait_for_selector(selectors['username'])
    
    # Fill username
    # Simulate real typing slightly better?
    page.fill(selectors['username'], username)
    
    # Fill password
    page.fill(selectors['password'], password)
    
    # IMPORTANT: Click away or tab out to trigger validation events?
    # Or click the password field again.
    page.click(selectors['password']) 
    
    # Wait a bit for JS validation to enable the button
    time.sleep(1) # Simple but effective
    
    # Check button state loop
    retries = 5
    for i in range(retries):
        submit_btn = page.locator(selectors['submit'])
        if not submit_btn.is_disabled():
            break
        
        print(f"   ⚠️ Submit button disabled. Retry {i+1}/{retries}...")
        
        # Action to trigger validation:
        # Clear and re-type one char? Or just focus/blur
        page.focus(selectors['password'])
        page.keyboard.press("End")
        page.keyboard.press("Space")
        page.keyboard.press("Backspace")
        
        time.sleep(1)
        
    # Click submit
    print("   → Clicking submit")
    page.click(selectors['submit'])
    
    # Wait for navigation to admin area
    print("   → Waiting for redirect to admin...")
    try:
        page.wait_for_url("**/admin**", timeout=45000, wait_until='domcontentloaded')
        print("   ✅ Redirected to admin.")
    except Exception as e:
        print(f"   ⚠️ Wait for redirect failed/timed out: {e}")
        # Proceed anyway to check if we have cookies, but likely will fail.
    
