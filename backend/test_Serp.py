from serpapi import GoogleSearch

params = {
  "engine": "google_ads_transparency_center",
  "advertiser_id": "AR07223290584121737217",
  "api_key": "65a56965c330dcb2d1dcdccb9e78f8309531c765a4f89d34f8c7c6c6bb90bdfa"
}

search = GoogleSearch(params)
results = search.get_dict()