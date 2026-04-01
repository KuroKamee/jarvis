"""
Web search (DuckDuckGo) and weather (wttr.in). No API keys needed.
"""

import httpx


async def web_search(query: str, max_results: int = 3) -> str:
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        return "\n".join(f"{r.get('title','')}: {r.get('body','')}" for r in results)
    except ImportError:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No results found."
            return "\n".join(f"{r.get('title','')}: {r.get('body','')}" for r in results)
        except ImportError:
            return "Search unavailable. Install with: pip3 install ddgs"
    except Exception as e:
        return f"Search error: {e}"


async def get_weather(location: str = "auto") -> str:
    try:
        url = f"https://wttr.in/{'' if location == 'auto' else location}?format=j1"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"User-Agent": "curl"})
            data = response.json()

        c = data["current_condition"][0]
        a = data["nearest_area"][0]
        city = a["areaName"][0]["value"]
        return (
            f"Location: {city}. {c['weatherDesc'][0]['value']}, "
            f"{c['temp_F']}F ({c['temp_C']}C), feels like {c['FeelsLikeF']}F. "
            f"Humidity {c['humidity']}%, wind {c['windspeedMiles']} mph."
        )
    except Exception as e:
        return f"Weather unavailable: {e}"
