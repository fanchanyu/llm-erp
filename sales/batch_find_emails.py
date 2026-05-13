#!/usr/bin/env python3
"""
Batch email finder for LLM-ERP customer list.
Processes high-potential companies (score 4-5) to find their website & email.
"""

import json
import subprocess
import re
import time
import sys
import os
from urllib.parse import urlparse, quote

INPUT_FILE = "/mnt/d/Project/LLM_ERP/sales/missing_emails_high_potential.json"
OUTPUT_FILE = "/mnt/d/Project/LLM_ERP/sales/found_emails.json"
PROGRESS_FILE = "/mnt/d/Project/LLM_ERP/sales/progress.json"

# Load companies
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    companies = json.load(f)

# Load progress if exists
found_results = {}
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        found_results = json.load(f)

processed_count = len(found_results)
skip_count = processed_count

print(f"Total high-potential companies: {len(companies)}")
print(f"Already processed: {skip_count}")

def google_search(query):
    """Search Google and return first result URL"""
    encoded = quote(query)
    cmd = [
        "curl", "-s", "-L", 
        f"https://www.google.com/search?q={encoded}&hl=zh-TW",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Accept-Language: zh-TW,zh;q=0.9,en;q=0.8",
        "--max-time", "10"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        html = result.stdout
        
        # Look for URLs in search results - Google format:
        # /url?q=https://...&...
        urls = re.findall(r'/url\?q=(https?://[^&"\']+)', html)
        if urls:
            return urls[0]
        
        # Alternative: direct links
        urls = re.findall(r'https?://(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s"<>]*)?', html)
        # Filter out Google domains
        real_urls = [u for u in urls if 'google.com' not in u and 'youtube.com' not in u]
        if real_urls:
            return real_urls[0]
    except Exception as e:
        print(f"  Search error: {e}")
    return None

def check_website_emails(domain):
    """Check common email patterns on a domain"""
    common_emails = [
        f"info@{domain}",
        f"contact@{domain}",
        f"service@{domain}",
        f"sales@{domain}",
        f"admin@{domain}",
    ]
    
    # Try to find email on contact page
    contact_urls = [
        f"https://{domain}/contact",
        f"https://{domain}/contact-us",
        f"https://{domain}/about",
        f"https://www.{domain}/contact",
    ]
    
    found = []
    for url in contact_urls:
        cmd = [
            "curl", "-s", "-L", url,
            "-H", "User-Agent: Mozilla/5.0",
            "--max-time", "8"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            html = result.stdout
            # Look for email patterns
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
            # Filter common ones
            for e in emails:
                if domain in e or any(kw in e.lower() for kw in ['info', 'contact', 'service', 'sales']):
                    if e not in found:
                        found.append(e)
        except:
            pass
    
    return found

def check_business_directories(company, tax_id, city):
    """Search Taiwan business directories"""
    encoded = quote(company)
    directories = [
        f"https://www.104.com.tw/company/search/?keyword={encoded}",
    ]
    
    for url in directories:
        cmd = [
            "curl", "-s", "-L", url,
            "-H", "User-Agent: Mozilla/5.0",
            "--max-time", "10"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            html = result.stdout
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
            if emails:
                return emails
        except:
            pass
    return None

def save_progress(results, count):
    """Save progress"""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    progress = {
        'total': len(companies),
        'processed': count,
        'found': len(results),
    }
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

# Process companies
for i, c in enumerate(companies):
    company = c['company']
    key = f"{company}|{c.get('tax_id', '')}"
    
    # Skip already found
    if key in found_results:
        continue
    
    print(f"[{skip_count+i+1}/{len(companies)}] {company} ({c['city']}, {c['category']})...", end=" ")
    sys.stdout.flush()
    
    result = {'company': company, 'tax_id': c.get('tax_id', ''), 'website': None, 'email': None, 'source': None}
    
    # Step 1: Google search for website
    search_query = f"{company} {c.get('city', '')} 官方網站"
    website = google_search(search_query)
    
    if website:
        # Clean URL
        parsed = urlparse(website)
        domain = parsed.netloc.replace('www.', '')
        result['website'] = f"https://{domain}"
        result['source'] = 'google_search'
        print(f"🌐 {domain}", end=" ")
        
        # Step 2: Check for email on website
        time.sleep(1)
        emails = check_website_emails(domain)
        if emails:
            result['email'] = emails[0]
            result['source'] = 'website_contact'
            print(f"📧 {emails[0]}")
        else:
            print("(no email found)")
    else:
        print("❌ no website found")
    
    # Save result
    if result['website'] or result['email']:
        found_results[key] = result
    
    # Save progress every 5
    if (i + 1) % 5 == 0 or i == len(companies) - 1:
        save_progress(found_results, skip_count + i + 1)
    
    # Rate limiting - be polite to Google
    time.sleep(3)

print(f"\n\n=== DONE ===")
print(f"Processed: {len(companies)}")
print(f"Found website/email: {len(found_results)}")
print(f"Results saved to: {OUTPUT_FILE}")
