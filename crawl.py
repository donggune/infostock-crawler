import asyncio
import os
import re
from datetime import date
from playwright.async_api import async_playwright
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TODAY = date.today().isoformat()

TARGETS = {
    "특징 테마":         "theme_feature",
    "특징 종목(코스피)": "kospi_feature",
    "특징 종목(코스닥)": "kosdaq_feature",
    "상한가 및 급등종목": "top_gainers",
}


async def click_row_by_title(page, keyword):
    rows = await page.query_selector_all("tbody tr")
    for row in rows:
        tds = await row.query_selector_all("td")
        for td in tds:
            text = await td.inner_text()
            if keyword in text:
                await row.evaluate("el => el.click()")
                await page.wait_for_timeout(1500)
                return True
    return False


async def parse_theme(page):
    """특징 테마 파싱: 테마명 / 이슈내용 행 추출"""
    records = []
    content_el = await page.query_selector(".txtCon:visible")
    if not content_el:
        # visible 속성이 없으면 모든 txtCon 중 마지막으로 보이는 것 사용
        els = await page.query_selector_all(".txtCon")
        for el in reversed(els):
            if await el.is_visible():
                content_el = el
                break
    if not content_el:
        print("테마: 내용 없음")
        return records

    rows = await content_el.query_selector_all("tr")
    i = 0
    while i < len(rows):
        tds = await rows[i].query_selector_all("td")
        if len(tds) == 2:
            left = (await tds[0].inner_text()).strip()
            right = (await tds[1].inner_text()).strip()
            # 헤더 행 제외, 테마시황 행 제외, 상세 설명 행(▷로 시작) 제외
            if left and left not in ["특징테마", "이 슈 요 약", "테마시황"] and not left.startswith("▷"):
                records.append({
                    "collected_date": TODAY,
                    "theme_name": left,
                    "description": right,
                })
        i += 1

    print(f"테마: {len(records)}건 파싱됨")
    return records


async def parse_stocks(page, category):
    """특징 종목(코스피/코스닥) 파싱: 종목명/코드/등락률/설명"""
    records = []
    content_el = None
    els = await page.query_selector_all(".txtCon")
    for el in reversed(els):
        if await el.is_visible():
            content_el = el
            break
    if not content_el:
        print(f"{category}: 내용 없음")
        return records

    rows = await content_el.query_selector_all("tr")
    for row in rows:
        tds = await row.query_selector_all("td")
        if len(tds) == 2:
            left = (await tds[0].inner_text()).strip()
            right = (await tds[1].inner_text()).strip()
            if not left or left in ["특징종목", "이슈요약", "이 슈 요 약"]:
                continue
            # 종목명(코드) 파싱
            match = re.search(r"([\w가-힣·&\s]+)\((\d{6}|\d{4}[A-Z]\d)\)", left)
            if match:
                stock_name = match.group(1).strip()
                stock_code = match.group(2)
                # 등락률 파싱
                rate_match = re.search(r"([+-]\d+\.\d+%)", left)
                change_rate = rate_match.group(1) if rate_match else None
                records.append({
                    "collected_date": TODAY,
                    "category": category,
                    "stock_name": stock_name,
                    "stock_code": stock_code,
                    "change_rate": change_rate,
                    "description": right,
                    "limit_up_days": None,
                })

    print(f"{category}: {len(records)}건 파싱됨")
    return records


async def parse_top_gainers(page):
    """특징 상한가 및 급등종목 파싱"""
    records = []
    content_el = None
    els = await page.query_selector_all(".txtCon")
    for el in reversed(els):
        if await el.is_visible():
            content_el = el
            break
    if not content_el:
        print("top_gainers: 내용 없음")
        return records

    rows = await content_el.query_selector_all("tr")
    for row in rows:
        tds = await row.query_selector_all("td")
        if len(tds) == 3:
            left = (await tds[0].inner_text()).strip()
            days_text = (await tds[1].inner_text()).strip()
            right = (await tds[2].inner_text()).strip()
            if not left or left in ["종 목", "상한가\n일수", "사유"]:
                continue
            match = re.search(r"([\w가-힣·&\s]+)\((\d{6}|\d{4}[A-Z]\d)\)", left)
            if match:
                stock_name = match.group(1).strip()
                stock_code = match.group(2)
                rate_match = re.search(r"([+-]\d+\.\d+%)", left)
                change_rate = rate_match.group(1) if rate_match else None
                try:
                    limit_up_days = int(days_text)
                except ValueError:
                    limit_up_days = None
                records.append({
                    "collected_date": TODAY,
                    "category": "top_gainers",
                    "stock_name": stock_name,
                    "stock_code": stock_code,
                    "change_rate": change_rate,
                    "description": right,
                    "limit_up_days": limit_up_days,
                })

    print(f"top_gainers: {len(records)}건 파싱됨")
    return records


def upsert_theme(records):
    if not records:
        return
    supabase.table("theme_issues").upsert(
        records, on_conflict="collected_date,theme_name"
    ).execute()
    print(f"theme_issues upsert 완료: {len(records)}건")


def upsert_stocks(records):
    if not records:
        return
    supabase.table("stock_issues").upsert(
        records, on_conflict="collected_date,category,stock_code"
    ).execute()
    print(f"stock_issues upsert 완료: {len(records)}건")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"=== 인포스탁 접속 중 ({TODAY}) ===")
        await page.goto("https://infostock.co.kr/MarketNews/TodaySummary")
        await page.wait_for_load_state("networkidle")

        rows = await page.query_selector_all("tbody tr")
        print(f"게시물 수: {len(rows)}")

        # 1. 특징 테마
        print("\n--- 특징 테마 수집 ---")
        found = await click_row_by_title(page, "특징 테마")
        if found:
            theme_records = await parse_theme(page)
            upsert_theme(theme_records)
        else:
            print("특징 테마 행을 찾지 못했습니다.")

        # 2. 특징 종목(코스피)
        print("\n--- 특징 종목(코스피) 수집 ---")
        found = await click_row_by_title(page, "특징 종목(코스피)")
        if found:
            kospi_records = await parse_stocks(page, "kospi_feature")
            upsert_stocks(kospi_records)

        # 3. 특징 종목(코스닥)
        print("\n--- 특징 종목(코스닥) 수집 ---")
        found = await click_row_by_title(page, "특징 종목(코스닥)")
        if found:
            kosdaq_records = await parse_stocks(page, "kosdaq_feature")
            upsert_stocks(kosdaq_records)

        # 4. 특징 상한가 및 급등종목
        print("\n--- 특징 상한가 및 급등종목 수집 ---")
        found = await click_row_by_title(page, "상한가 및 급등종목")
        if found:
            gainers_records = await parse_top_gainers(page)
            upsert_stocks(gainers_records)

        await browser.close()
        print("\n=== 수집 완료 ===")


asyncio.run(main())
