import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("=== 인포스탁 접속 중 ===")
        await page.goto("https://infostock.co.kr/MarketNews/TodaySummary")
        await page.wait_for_load_state("networkidle")

        # tr.cursor 클래스로 실제 게시물 목록 행만 선택 (tbody tr 전체 X)
        rows = await page.query_selector_all("tr.cursor")
        print(f"게시물 수: {len(rows)}")

        if rows:
            await rows[-1].evaluate("el => el.click()")
            try:
                await page.wait_for_function(
                    "document.querySelector('.txtCon')?.innerText?.trim().length > 10",
                    timeout=5000
                )
            except Exception:
                await page.wait_for_timeout(2000)

            content_el = await page.query_selector(".txtCon")
            if content_el:
                text = await content_el.inner_text()
                print("=== 수집된 내용 (처음 500자) ===")
                print(text[:500])
                print("\n=== 수집 성공! ===")
            else:
                print("내용을 찾을 수 없습니다.")

        await browser.close()

asyncio.run(main())
