"""
Test script for 10-K components
"""
import asyncio
from datetime import date
from src.ingestion.edgar_client import SECEdgarClient
from src.ingestion.form10k_parser import Form10KParser


async def test():
    # Test 1: Search for Apple 10-K filings
    print('=== Testing EDGAR Client ===')
    client = SECEdgarClient(user_agent='Form13F AI Agent hodolhodol0@gmail.com')

    try:
        # Search for 2023 10-K
        print('Searching for Apple 10-K filings in 2023...')
        filings = await client.search_filings(
            cik='0000320193',
            form_type='10-K',
            date_from=date(2023, 1, 1),
            date_to=date(2023, 12, 31),
            limit=1
        )

        if not filings:
            print('ERROR: No filings found')
            return

        filing = filings[0]
        print(f'SUCCESS: Found filing {filing.accession_number} filed on {filing.filing_date}')

        # Download 10-K
        print(f'Downloading 10-K filing...')
        html = await client.download_10k_filing(filing.accession_number, '0000320193')
        print(f'SUCCESS: Downloaded {len(html):,} bytes')

        # Test 2: Parse 10-K
        print('')
        print('=== Testing 10-K Parser ===')
        parser = Form10KParser()
        sections = parser.parse_html(html)

        print(f'SUCCESS: Extracted {len(sections)} sections:')
        for section_name, text in sections.items():
            print(f'  - {section_name}: {len(text):,} characters')

        # Show a snippet from Item 1A
        if 'Item 1A' in sections:
            snippet = sections['Item 1A'][:500]
            print('')
            print('=== Sample from Item 1A: Risk Factors ===')
            print(snippet + '...')

    finally:
        await client.close()


# Run the test
if __name__ == '__main__':
    asyncio.run(test())
