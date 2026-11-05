# Commercial distribution/API rights gate — Coin Candle Collector

Verified on **2026-11-05 KST**, for `hibi89/candle_scraper` v1.6.1 commercial plans.

## Finding — Upbit paid EXE distribution has an explicit contractual block

Official current Upbit Open API terms reproduced in the Upbit Developer Center:
- [Upbit Developer Center — Open API 이용약관](https://docs.upbit.com/kr/)
- [Upbit official 2024-10-30 terms revision notice](https://docs.upbit.com/kr/v1.5.9/changelog/open-api-%EC%9D%B4%EC%9A%A9%EC%95%BD%EA%B4%80-%EA%B0%9C%EC%A0%95-%EC%95%88%EB%82%B4-1015-%EC%A0%81%EC%9A%A9-%EC%98%88%EC%A0%95)
- [Upbit's explicit notice on paid program distribution (historical wording)](https://docs.upbit.com/kr/v1.5.9/changelog/%EC%95%88%EB%82%B4-open-api-%ED%82%A4-%EC%A0%95%EB%B3%B4-%EB%B3%B4%EC%95%88-%EC%A3%BC%EC%9D%98-%EC%95%88%EB%82%B4-%EB%B0%8F-%EC%9D%B4%EC%9A%A9%EC%95%BD%EA%B4%80-%EC%95%88%EB%82%B4-%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%A8-%EC%9C%A0%EC%83%81-%ED%8C%90%EB%A7%A4-%EB%B6%88%EA%B0%80)

The currently published terms' **Article 6(3)** disallows transferring, distributing, or licensing for payment any program capable of using the Upbit Open API. **Article 5** restricts unauthorized commercial use of Open API/Docs content or data. An EXE with Upbit public candle API calls falls within a serious distribution risk even though no API key is embedded. A program working technically, a public no-key endpoint, or lack of included candles **does not establish commercial permission**.

**Release action: Upbit-only and combined paid editions are BLOCKED unless explicit written permission/license from Upbit is obtained, or the product is redesigned and validated to avoid the prohibited connection.** Do not publish, take payment, send a customer ZIP, or describe the product as approved.

## Bithumb cannot be assumed commercially cleared

Bithumb's [public API reference](https://apidocs.bithumb.com/reference/api-%EB%A0%88%ED%8D%BC%EB%9F%B0%EC%8A%A4) describes access without API keys, and [public API limits](https://apidocs.bithumb.com/docs/api-%25EC%259A%2594%25EC%25B2%25AD-%25EC%2588%2598-%25EC%25A0%259C%25ED%2595%259C-%25EC%2595%2588%25EB%2582%25B4) describe rate restrictions; neither alone grants rights to sell a data-collecting EXE or sublicense market data. Obtain current *official* commercial distribution and data-use conditions / written permission from Bithumb before sale. Third-party/archived terms are not adequate proof of present permission.


### Bithumb's historical API terms: direct data-transfer prohibition

A separately published Bithumb API agreement on Bithumb's official domain (PDF filename `20180911_bithumb_APIService.pdf`, effective **2018-10-18**) contains **Article 6(1)(4)**, barring the transfer to other persons of investment information, quotations, balance, trade details, etc. obtained from the API: [official older terms PDF](https://www.bithumb.com/resources/data/20180911_bithumb_APIService.pdf). The [Bithumb API Service Terms page](https://en.m.bithumb.com/member_operation/info_api) currently indexed by search also reports an equivalent Article 6 restriction, but the direct page could not be loaded due to a redirect loop at verification. The historical PDF is **not proof of what later revisions permit**.

Consequence: do not bundle or redistribute fetched candle data, market DBs, exported CSVs, or customer data with any paid package. This separate prohibition **does not prove that selling a no-data Bithumb-only collector EXE is allowed or prohibited**; confirm current terms and explicit written distribution permission with Bithumb. Current public endpoint availability is not a resale license.

## Options requiring owner choice before material product scope change

1. **Permission-first (preserves current 3 EXEs):** request explicit commercial API software redistribution and market-data handling approval from Upbit and Bithumb. Development cost minimal; timetable/price and approval uncertain. Recommended to preserve current intended product if permission is granted.
2. **Licensed commercial provider:** replace restricted exchange API connections with a provider whose license explicitly allows resale/EXE distribution, while preserving UI and SQLite contract. Technical cost and possible subscription fees; requires price/terms approval.
3. **Offline CSV/SQLite tool (no embedded exchange API calls):** sell local CSV import, quality checks, cleaning, de-duplication, refresh from customer-supplied licensed files. Most controllable commercial scope, but changes the product promise and requires separate functional tests and owner approval. Do not redistribute market data.

**No new launch claims from passing Windows CI or live API tests.** This is a release policy and licensing blocker, not a failing unit test. A legal professional or the provider should confirm any exceptional permission. Any paid API, external transfer, change of product scope or source/sales material requires owner approval.

## Related source/technical evidence
- `STATUS.md` and `HANDOFF.md`: source/CI SHA, actual Windows EXE launch proof and limitations.
- `docs/RELEASE_CHECKLIST.md`: release is HOLD until **technical and contractual** gates independently pass.
