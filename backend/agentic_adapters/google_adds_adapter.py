from apify_client import ApifyClient
import json
import os
import requests
import urllib.parse
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class GoogleAdsScraperPipeline:
    """Pipeline for searching and scraping Google Ads Transparency data"""
    
    def __init__(self):
        """
        Initialize the scraper with API keys
        
        Args:
            serpapi_key: SerpAPI key (if None, loads from env)
            apify_token: Apify API token (if None, loads from env)
        """
        self.serpapi_key = os.getenv("SERPER_API_KEY")
        self.apify_token = os.getenv("APIFY_API_TOKEN")
        self.apify_client = ApifyClient(self.apify_token)
    
    async def search_advertiser(self, domain: str, region: str = "RO") -> Dict:
        """
        Search for advertiser using SerpAPI
        
        Args:
            domain: Domain to search for (e.g., "hubspot.com")
            
        Returns:
            Dict with advertiser_id, region, and full API response
        """
        
        response = requests.get("https://serpapi.com/search", params={
            "engine": "google_ads_transparency_center",
            "text": domain,
            "api_key": self.serpapi_key
        })
        
        data = response.json()
        
        if "ad_creatives" not in data or len(data["ad_creatives"]) == 0:
            raise ValueError(f"No ads found for {domain}!")
        
        # Get advertiser info
        first_ad = data["ad_creatives"][0]
        advertiser_id = first_ad["advertiser_id"]
        details_url = first_ad.get("details_link", "")
        
        return {
            "advertiser_id": advertiser_id,
            "region": region,
            "full_response": data
        }
    
    async def scrape_ads(
        self,
        advertiser_id: str,
        region: str = "RO",
        results_limit: int = 10,
        skip_details: bool = False,
        download_assets: bool = False,
        download_previews: bool = False,
        use_ocr: bool = True,
        preset_date: str = "Last+4+days"
    ) -> List[Dict]:
        """
        Scrape ads using Apify actor
        
        Args:
            advertiser_id: Google Ads advertiser ID
            region: Region code (e.g., "RO", "ES")
            results_limit: Maximum number of results
            skip_details: Skip detailed information
            download_assets: Download ad assets
            download_previews: Download ad previews
            use_ocr: Use OCR on images
            preset_date: Time period (e.g., "Last+4+days", "Last+30+days")
            
        Returns:
            List of ad variations
        """
        url = f"https://adstransparency.google.com/advertiser/{advertiser_id}?authuser=0&region={region}&preset-date={preset_date}"
        
        input_data = {
            "startUrls": [{"url": url}],
            "resultsLimit": results_limit,
            "skipDetails": skip_details,
            "shouldDownloadAssets": download_assets,
            "shouldDownloadPreviews": download_previews,
            "ocr": use_ocr,
            "proxyConfiguration": {
                "apifyProxyGroups": [],
                "useApifyProxy": True
            }
        }
        # Run the Actor
        run = self.apify_client.actor("silva95gustavo/google-ads-scraper").call(run_input=input_data)
        
        # Extract results
        results = []
        for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            if "variations" in item:
                results.append(item["variations"])
        return results
    
    