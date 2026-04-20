#!/usr/bin/env python3
"""
Browser Automation with Selenium
Examples of automating web browser interactions
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

class BrowserAutomation:
    def __init__(self, headless=False):
        """Initialize the browser automation"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # You'll need to download chromedriver and set the path
        # service = Service('/path/to/chromedriver')
        # self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # For demo purposes, we'll create a mock version
        self.driver = None
        print("Browser automation initialized (demo mode)")
        
    def setup_driver(self):
        """Setup the webdriver (requires chromedriver)"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            print(f"Error setting up driver: {e}")
            print("Please install chromedriver: https://sites.google.com/chromium.org/driver/")
            return False
    
    def demo_search_automation(self):
        """Demo: Automate Google search"""
        if not self.setup_driver():
            return
            
        try:
            # Navigate to Google
            self.driver.get("https://www.google.com")
            print("Navigated to Google")
            
            # Find search box and enter query
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.send_keys("Selenium automation")
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "search"))
            )
            
            # Get search results
            results = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
            print(f"Found {len(results)} search results")
            
            # Print first few results
            for i, result in enumerate(results[:3]):
                try:
                    title = result.find_element(By.CSS_SELECTOR, "h3")
                    print(f"{i+1}. {title.text}")
                except:
                    continue
                    
        except Exception as e:
            print(f"Error during search automation: {e}")
        finally:
            self.driver.quit()
    
    def demo_form_filling(self):
        """Demo: Automate form filling"""
        if not self.setup_driver():
            return
            
        try:
            # Create a simple HTML form for demo
            html_content = """
            <!DOCTYPE html>
            <html>
            <body>
                <form id="demoForm">
                    <input type="text" id="name" placeholder="Name">
                    <input type="email" id="email" placeholder="Email">
                    <textarea id="message" placeholder="Message"></textarea>
                    <button type="submit">Submit</button>
                </form>
            </body>
            </html>
            """
            
            # Save and open the HTML file
            with open("demo_form.html", "w") as f:
                f.write(html_content)
            
            self.driver.get(f"file://{os.path.abspath('demo_form.html')}")
            
            # Fill the form
            name_field = self.driver.find_element(By.ID, "name")
            email_field = self.driver.find_element(By.ID, "email")
            message_field = self.driver.find_element(By.ID, "message")
            
            name_field.send_keys("John Doe")
            email_field.send_keys("john@example.com")
            message_field.send_keys("This is a test message from Selenium!")
            
            print("Form filled successfully")
            
            # Submit the form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            time.sleep(2)  # Wait to see the result
            
        except Exception as e:
            print(f"Error during form automation: {e}")
        finally:
            self.driver.quit()
            # Clean up
            if os.path.exists("demo_form.html"):
                os.remove("demo_form.html")
    
    def demo_scrolling_and_clicking(self):
        """Demo: Automate scrolling and clicking"""
        if not self.setup_driver():
            return
            
        try:
            # Navigate to a page with scrollable content
            self.driver.get("https://httpbin.org/headers")
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Click on an element (if available)
            try:
                # This is just an example - the actual element would depend on the page
                element = self.driver.find_element(By.TAG_NAME, "body")
                element.click()
                print("Clicked on page element")
            except:
                print("No clickable element found")
                
        except Exception as e:
            print(f"Error during scrolling automation: {e}")
        finally:
            self.driver.quit()

# Demo functions that don't require actual browser
class MockBrowserAutomation:
    """Mock browser automation for demonstration"""
    
    @staticmethod
    def show_code_examples():
        """Show examples of browser automation code"""
        print("=== Browser Automation Examples ===")
        print("\n1. Basic Navigation:")
        print("""
        from selenium import webdriver
        driver = webdriver.Chrome()
        driver.get("https://www.google.com")
        """)
        
        print("\n2. Finding Elements:")
        print("""
        # By ID
        element = driver.find_element(By.ID, "element_id")
        
        # By CSS Selector
        element = driver.find_element(By.CSS_SELECTOR, ".class-name")
        
        # By XPath
        element = driver.find_element(By.XPATH, "//div[@class='example']")
        """)
        
        print("\n3. Interacting with Elements:")
        print("""
        # Click
        element.click()
        
        # Send keys (type text)
        element.send_keys("Hello World")
        
        # Clear field
        element.clear()
        
        # Submit form
        element.submit()
        """)
        
        print("\n4. Waiting for Elements:")
        print("""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.presence_of_element_located((By.ID, "dynamic-element")))
        """)

if __name__ == "__main__":
    # Demo the mock automation
    mock = MockBrowserAutomation()
    mock.show_code_examples()
    
    # Uncomment to try real automation (requires chromedriver)
    # automation = BrowserAutomation()
    # automation.demo_search_automation()
