# کاتالوگ مسیرهای TSETMC/TSE

تعداد inventory: 136 مسیر خواندن داده در 19 خانواده. این inventory عمومی شناسایی‌شده است؛ فهرست رسمی کامل یا تأیید زنده تمام مسیرها نیست. برای پارامترهای نماد، تاریخ، حراج و اطلاعیه باید شناسه واقعی ارائه شود.

چهار مسیر اصلی با شناسه‌های market_watch، client_all، indices و price_history در دسترس‌اند. املای SelectedIndexes از مرجع پیاده‌سازی استخراج شده و SelectedIndices پیام کاربر نیز جدا به‌عنوان نامزد ثبت شده است. هیچ‌یک در این محیط پاسخ داده معتبر نداده‌اند.

| خانواده | تعداد مسیر |
|---|---:|
| BestLimits | 6 |
| ClientType | 6 |
| ClosingPrice | 32 |
| Codal | 11 |
| Energy | 5 |
| Fund | 6 |
| Index | 11 |
| Instrument | 6 |
| InstrumentProvider | 22 |
| Learning | 1 |
| MarketData | 8 |
| Msg | 4 |
| Shareholder | 5 |
| StaticData | 2 |
| Supervision | 1 |
| Trade | 4 |
| cmssite | 4 |
| tsev2 | 1 |
| v1 | 1 |

## قرارداد مسیرها

| شناسه | میزبان | مسیر | پارامترهای قالب | فرمت |
|---|---|---|---|---|
| bestlimits_5d44bb32 | cdn.tsetmc.com | `/api/BestLimits/{insCode}` | insCode | json |
| bestlimitshistory_b6486262 | cdn.tsetmc.com | `/api/BestLimits/{insCode}/{dEven}` | insCode, dEven | json |
| bestlimitstop_64b6792f | cdn.tsetmc.com | `/api/BestLimits/GetBestLimitsTop/{flow}` | flow | json |
| bestlimitstoppower_a7a54b21 | cdn.tsetmc.com | `/api/BestLimits/GetBestLimitsTopPower/` | — | json |
| bubble_chart_3ad6615e | webgw.tse.ir | `/InstrumentProvider/api/v1/ChartSummary/BubbleChart/fa` | — | json |
| chartdata_1ab326a4 | cdn.tsetmc.com | `/api/ClosingPrice/GetChartData/{insCode}/{resolution}` | insCode, resolution | json |
| chartdata_daily_59acf75a | cdn.tsetmc.com | `/api/ClosingPrice/GetChartData/{InsCode}/D` | InsCode | json |
| client_all | cdn.tsetmc.com | `/api/ClientType/GetClientTypeAll` | — | json |
| client_history | cdn.tsetmc.com | `/api/ClientType/GetClientTypeHistory/{InsCode}/{DEven}` | InsCode, DEven | json |
| clienttype_dae6df5c | cdn.tsetmc.com | `/api/ClientType/GetClientType/{insCode}/1/0` | insCode | json |
| clienttype_now_626f5761 | cdn.tsetmc.com | `/api/ClientType/GetClientType/{InsCode}/1/0` | InsCode | json |
| clienttypehistory_59424287 | cdn.tsetmc.com | `/api/ClientType/GetClientTypeHistory/{insCode}` | insCode | json |
| clienttypehistorydate_e16fe872 | cdn.tsetmc.com | `/api/ClientType/GetClientTypeHistory/{insCode}/{dEven}` | insCode, dEven | json |
| closing_info | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceInfo/{InsCode}` | InsCode | json |
| closingprice_daily_57c13680 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDaily/{InsCode}/{DEven}` | InsCode, DEven | json |
| closingprice_daily_list_csv_a8c718d0 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDailyListCSV/{InsCode}/0` | InsCode | text |
| closingprice_daily_list_top_fb373a94 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDailyList/{InsCode}/{Top}` | InsCode, Top | json |
| closingprice_history_2a89a433 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceHistory/{InsCode}/{DEven}` | InsCode, DEven | json |
| closingpricedaily_29c32881 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDaily/{insCode}/{dEven}` | insCode, dEven | json |
| closingpricedailyallinst_f22fc53d | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDailyAllInst` | — | json |
| closingpricedailycsv_1b42755f | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDailyListCSV/{insCode}/{prependCol}` | insCode, prependCol | text |
| closingpricedailylist_ce186984 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDailyList/{insCode}/{top}` | insCode, top | json |
| closingpricehistory_5f507827 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceHistory/{insCode}/{dEven}` | insCode, dEven | json |
| closingpriceinfo_ccbb2b54 | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceInfo/{insCode}` | insCode | json |
| cms_announcements_62d7a0a0 | webgw.tse.ir | `/cmssite/api/v1/Notice/SimpleList/fa?CategoryId=Announcement&PageSize={n}` | n | json |
| cms_banner_df60e5e6 | webgw.tse.ir | `/cmssite/api/v1/Banner/List/fa` | — | json |
| cms_menu_5a55a3fa | webgw.tse.ir | `/cmssite/api/v1/Menu/MainMenu/fa` | — | json |
| cms_news_a560a853 | webgw.tse.ir | `/cmssite/api/v1/Notice/SimpleList/fa?CategoryId=News&PageSize={n}` | n | json |
| codal_publisher_by_symbol_e377c4c2 | cdn.tsetmc.com | `/api/Codal/GetCodalPublisherBySymbol/{Symbol}` | Symbol | json |
| codalattachmentbyrow_ffa0cec7 | cdn.tsetmc.com | `/api/Codal/GetFileAttachmentByMainTableRowId/` | — | json |
| codalattachmentspecific_450ea71e | cdn.tsetmc.com | `/api/Codal/GetAttachmentContentFileByTracingNoAndRowOrder/` | — | binary |
| codalbyinstrument_f1f3f801 | cdn.tsetmc.com | `/api/Codal/GetPreparedDataByInsCode/{top}/{insCode}` | top, insCode | json |
| codalprepared_021dfaa0 | cdn.tsetmc.com | `/api/Codal/GetPreparedData/{top}` | top | json |
| codalpublisher_cd849714 | cdn.tsetmc.com | `/api/Codal/GetCodalPublisherBySymbol/{symbol}` | symbol | json |
| codalstatement_3bb4a44a | cdn.tsetmc.com | `/api/Codal/GetStatementContentByInsCode/{type}/{subType}/{page}/{insCode}` | type, subType, page, insCode | json |
| company_state_9371eb36 | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/CompanyState/fa` | — | json |
| endpoint_1309e5a4 | cdn.tsetmc.com | `/api/Index/GetInstEffect/0/2/7` | — | json |
| endpoint_94e03c25 | cdn.tsetmc.com | `/api/Index/GetInstEffect/0/1/7` | — | json |
| endpoint_b9d5a250 | cdn.tsetmc.com | `/api/Index/GetIndexB1LastAll/SelectedIndexes/2` | — | json |
| endpoint_c7b94d45 | cdn.tsetmc.com | `/api/ClosingPrice/GetIndexCompany/{insCode}` | insCode | json |
| endpoint_dae602ab | cdn.tsetmc.com | `/api/Index/GetIndexB1LastAll/All/1` | — | json |
| endpoint_dcb1143a | cdn.tsetmc.com | `/api/Index/GetIndexB1LastAll/All/2` | — | json |
| energy_auction_by_id_56b41dd5 | cdn.tsetmc.com | `/api/Energy/GetAuctionById/{AuctionId}` | AuctionId | json |
| energy_auction_trade_by_id_d3a5e5c0 | cdn.tsetmc.com | `/api/Energy/GetAuctionTradeById/{AuctionId}` | AuctionId | json |
| energyauctionlist_19c6bb51 | cdn.tsetmc.com | `/api/Energy/GetGetAuctionListItemByType/{type}/{top}/{extra}` | type, top, extra | json |
| energyauctionoverview_72bc3f10 | cdn.tsetmc.com | `/api/Energy/GetAuctionOverview/{flow}` | flow | json |
| energypoweroverview_e6f88d60 | cdn.tsetmc.com | `/api/Energy/GetPowerOverview/` | — | json |
| etf_by_inscode_a74c0171 | cdn.tsetmc.com | `/api/Fund/GetETFByInsCode/{InsCode}` | InsCode | json |
| file_attachment_by_row_id_4908c8ae | cdn.tsetmc.com | `/api/Codal/GetFileAttachmentByMainTableRowId/{MainTableRowId}` | MainTableRowId | json |
| file_attachment_by_tracing_8a50ef0a | cdn.tsetmc.com | `/api/Codal/GetFileAttachmentByTracingNo/{TracingNo}` | TracingNo | json |
| fund_detail_0_80c7369d | cdn.tsetmc.com | `/api/Fund/GetFundInDetail/0` | — | json |
| fund_detail_1_8b9278ce | cdn.tsetmc.com | `/api/Fund/GetFundInDetail/1` | — | json |
| getetfbyinscode_a2127c1f | cdn.tsetmc.com | `/api/Fund/GetETFByInsCode/{insCode}` | insCode | json |
| getfundindetail_8bb52846 | cdn.tsetmc.com | `/api/Fund/GetFundInDetail/{no}` | no | json |
| getfunds_19015120 | cdn.tsetmc.com | `/api/Fund/GetFunds/{type}` | type | json |
| getindexb1lastall_5da642ce | cdn.tsetmc.com | `/api/Index/GetIndexB1LastAll/SelectedIndexes/{flow}` | flow | json |
| getindexb1lastday_3f471c63 | cdn.tsetmc.com | `/api/Index/GetIndexB1LastDay/{insCode}` | insCode | json |
| getindexb2history_424e02db | cdn.tsetmc.com | `/api/Index/GetIndexB2History/{insCode}` | insCode | json |
| getinsteffect_634d8942 | cdn.tsetmc.com | `/api/Index/GetInstEffect/{extra}/{flow}/{top}` | extra, flow, top | json |
| getinstrumentstatistic_18a5a2c7 | cdn.tsetmc.com | `/api/MarketData/GetInstrumentStatistic/{insCode}` | insCode | json |
| getmsgbyflow_a2fac475 | cdn.tsetmc.com | `/api/Msg/GetMsgByFlow/{flow}/{top}` | flow, top | json |
| getmsgbyinscode_58e775eb | cdn.tsetmc.com | `/api/Msg/GetMsgByInsCode/{insCode}` | insCode | json |
| getsupervisionbyinscode_304c0a86 | cdn.tsetmc.com | `/api/Supervision/GetSupervisionByInsCode/` | — | json |
| history_archive_5bd2d01f | webgw.tse.ir | `/InstrumentProvider/api/v1/History/Archive/fa?InstrumentId={ISIN}` | ISIN | json |
| index_live_by_id_fdfae86f | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/IndexLiveById/fa?InstrumentId={InstrumentId}` | InstrumentId | json |
| index_spelling_supplied_by_user_84c637c1 | cdn.tsetmc.com | `/api/Index/GetIndexB1LastAll/SelectedIndices/1` | — | json |
| indices | cdn.tsetmc.com | `/api/Index/GetIndexB1LastAll/SelectedIndexes/1` | — | json |
| inst_value_all_params_a9f60cfb | cdn.tsetmc.com | `/api/MarketData/GetInstValueAllInstAllParam` | — | json |
| instrument_calendar_1102aafd | cdn.tsetmc.com | `/api/ClosingPrice/GetInstrumentCalendar/{InsCode}` | InsCode | json |
| instrument_client_type_ce88946d | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/InstrumentClientType/fa?InstrumentId={ISIN}` | ISIN | json |
| instrument_history_ddd57c97 | cdn.tsetmc.com | `/api/Instrument/GetInstrumentHistory/{InsCode}/{DEven}` | InsCode, DEven | json |
| instrument_identity_abdee117 | cdn.tsetmc.com | `/api/Instrument/GetInstrumentIdentity/{InsCode}` | InsCode | json |
| instrument_info | cdn.tsetmc.com | `/api/Instrument/GetInstrumentInfo/{InsCode}` | InsCode | json |
| instrument_search | cdn.tsetmc.com | `/api/Instrument/GetInstrumentSearch/{Query}` | Query | json |
| instrument_shortcut_search_3ad87e82 | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/InstrumentShortcut/fa?SimpleSearchText={query}&MarketCategoryIds[0]={cat}&PageNumber={n}&PageSize={size}` | query, cat, n, size | json |
| instrument_slider_0d7a9d04 | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/InstrumentSliderQuery/fa` | — | json |
| instrument_slider_by_industry_687425e3 | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/InstrumentSliderQuery/fa?IndustryId={IndustryId}` | IndustryId | json |
| instrument_state_073c4f54 | cdn.tsetmc.com | `/api/MarketData/GetInstrumentState/{InsCode}/{DEven}` | InsCode, DEven | json |
| instrument_state_top_f0d90fa2 | cdn.tsetmc.com | `/api/MarketData/GetInstrumentStateTop/{Top}` | Top | json |
| instrument_statistic_1122cdea | cdn.tsetmc.com | `/api/MarketData/GetInstrumentStatistic/{InsCode}` | InsCode | json |
| instrumentcalendar_c3c8068a | cdn.tsetmc.com | `/api/ClosingPrice/GetInstrumentCalendar/{insCode}` | insCode | json |
| instruments_history_in_day_ee69f513 | cdn.tsetmc.com | `/api/ClosingPrice/GetInstrmentsHistoryInDay/{DEven}` | DEven | json |
| instrumentshistoryinday_94f50e52 | cdn.tsetmc.com | `/api/ClosingPrice/GetInstrmentsHistoryInDay/{dEven}` | dEven | json |
| learning_topics_fff8a405 | cdn.tsetmc.com | `/api/Learning/GetLearningTopics` | — | json |
| live_instrument_by_id_60c7d41f | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/LiveInstrumentByIdQuery/fa?InstrumentId={ISIN}` | ISIN | json |
| live_instrument_summary_by_id_8639f552 | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/LiveInstrumentSummaryByIdQuery/fa?InstrumentId={ISIN}` | ISIN | json |
| market_date_4edcde2d | webgw.tse.ir | `/api/v1/PublicData/MarketDate/fa` | — | json |
| market_overview_87bc6818 | cdn.tsetmc.com | `/api/MarketData/GetMarketOverview/{Flow}` | Flow | json |
| market_summary_ffdb3a2b | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/MarketSummary/fa` | — | json |
| market_watch | cdn.tsetmc.com | `/api/ClosingPrice/GetMarketWatch` | — | json |
| market_watch_excel_legacy_bd030c12 | old.tsetmc.com | `/tsev2/excel/MarketWatchPlus.aspx?d=0` | — | binary |
| marketcap_69a6c096 | cdn.tsetmc.com | `/api/ClosingPrice/GetMarketCap/` | — | json |
| marketmap_27bd3517 | cdn.tsetmc.com | `/api/ClosingPrice/GetMarketMap` | — | json |
| marketwatch_cash_3dbd6fbd | webgw.tse.ir | `/InstrumentProvider/api/v1/MarketWatch/MarketWatchCash/fa` | — | json |
| marketwatch_debt_317ceefd | webgw.tse.ir | `/InstrumentProvider/api/v1/MarketWatch/MarketWatchDebt/fa` | — | json |
| marketwatch_etf_afa61d8f | webgw.tse.ir | `/InstrumentProvider/api/v1/MarketWatch/MarketWatchEtf/fa` | — | json |
| marketwatch_future_b0a0b362 | webgw.tse.ir | `/InstrumentProvider/api/v1/MarketWatch/MarketWatchFuture/fa` | — | json |
| marketwatch_option_7ae026a4 | webgw.tse.ir | `/InstrumentProvider/api/v1/MarketWatch/MarketWatchOption/fa` | — | json |
| marketwatch_talmarket_36de1ef4 | webgw.tse.ir | `/InstrumentProvider/api/v1/MarketWatch/MarketWatchTALMarket/fa` | — | json |
| marketwatch_tradeoption_29cd9c27 | webgw.tse.ir | `/InstrumentProvider/api/v1/MarketWatch/MarketWatchTradeOption/fa` | — | json |
| marketwatchexcel_82c464e3 | cdn.tsetmc.com | `/api/ClosingPrice/GetMarketWatchExcel/` | — | binary |
| messages_by_flow_8539f872 | cdn.tsetmc.com | `/api/Msg/GetMsgByFlow/{Flow}/{Top}` | Flow, Top | json |
| messages_by_inscode_b0113d54 | cdn.tsetmc.com | `/api/Msg/GetMsgByInsCode/{InsCode}` | InsCode | json |
| order_book | cdn.tsetmc.com | `/api/BestLimits/{InsCode}` | InsCode | json |
| order_book_history | cdn.tsetmc.com | `/api/BestLimits/{InsCode}/{DEven}` | InsCode, DEven | json |
| prepared_data_by_inscode_df5986f4 | cdn.tsetmc.com | `/api/Codal/GetPreparedDataByInsCode/{Top}/{InsCode}` | Top, InsCode | json |
| prepared_data_top_6512c496 | cdn.tsetmc.com | `/api/Codal/GetPreparedData/{Top}` | Top | json |
| price_adjust_by_flow_b9738537 | cdn.tsetmc.com | `/api/ClosingPrice/GetPriceAdjustByFlow/{Flow}/{Top}` | Flow, Top | json |
| price_adjustments | cdn.tsetmc.com | `/api/ClosingPrice/GetPriceAdjustList/{InsCode}` | InsCode | json |
| price_history | cdn.tsetmc.com | `/api/ClosingPrice/GetClosingPriceDailyList/{InsCode}/0` | InsCode | json |
| priceadjustbyflow_aa1de9f3 | cdn.tsetmc.com | `/api/ClosingPrice/GetPriceAdjustByFlow/{flow}/{top}` | flow, top | json |
| priceadjustlist_ab930d53 | cdn.tsetmc.com | `/api/ClosingPrice/GetPriceAdjustList/{insCode}` | insCode | json |
| related_company_d60b8e1f | cdn.tsetmc.com | `/api/ClosingPrice/GetRelatedCompany/{CSecVal}` | CSecVal | json |
| relatedcompanies_84404573 | cdn.tsetmc.com | `/api/ClosingPrice/GetRelatedCompany/{cSecVal}` | cSecVal | json |
| same_group_company_555f94ca | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/SameGroupCompany/fa?InstrumentId={ISIN}` | ISIN | json |
| same_group_company_query_9476c06e | webgw.tse.ir | `/InstrumentProvider/api/v1/Instrument/SameGroupCompanyQuery/fa?InstrumentId={ISIN}` | ISIN | json |
| sectors_summary_a42d5ff4 | cdn.tsetmc.com | `/api/MarketData/GetSectorsSummary` | — | json |
| share_change_4e72ef4c | cdn.tsetmc.com | `/api/Instrument/GetInstrumentShareChange/{InsCode}` | InsCode | json |
| share_change_by_flow_028a8cd6 | cdn.tsetmc.com | `/api/Instrument/GetInstrumentShareChangeByFlow/{Flow}/{Top}` | Flow, Top | json |
| shareholder_changes_all_93a6a707 | cdn.tsetmc.com | `/api/Shareholder/GetShareHolderChanges/false` | — | json |
| shareholder_changes_old_49998b86 | cdn.tsetmc.com | `/api/Shareholder/{InsCode}/{DEven}` | InsCode, DEven | json |
| shareholder_company_list_a4546374 | cdn.tsetmc.com | `/api/Shareholder/GetShareHolderCompanyList/{ShareHolderShareID}` | ShareHolderShareID | json |
| shareholder_history_53ca08e8 | cdn.tsetmc.com | `/api/Shareholder/GetShareHolderHistory/{InsCode}/{DEven}/{Top}` | InsCode, DEven, Top | json |
| shareholder_last_6876cb23 | cdn.tsetmc.com | `/api/Shareholder/GetInstrumentShareHolderLast/{InsCode}` | InsCode | json |
| static_data_016c2c3f | cdn.tsetmc.com | `/api/StaticData/GetStaticData` | — | json |
| static_threshold_b78d620e | cdn.tsetmc.com | `/api/MarketData/GetStaticThreshold/{InsCode}/{DEven}` | InsCode, DEven | json |
| time_b6c34faa | cdn.tsetmc.com | `/api/StaticData/GetTime` | — | text |
| trade_history | cdn.tsetmc.com | `/api/Trade/GetTradeHistory/{InsCode}/{DEven}/false` | InsCode, DEven | json |
| trade_intraday_6a8c1d2e | cdn.tsetmc.com | `/api/Trade/GetTradeIntraDay/{InsCode}` | InsCode | json |
| trade_now_c4fc76bf | cdn.tsetmc.com | `/api/Trade/GetTrade/{InsCode}` | InsCode | json |
| trade_volume_6be4736a | cdn.tsetmc.com | `/api/Trade/GetTradeVolume/{InsCode}` | InsCode | json |
| tradetopmostvisited_5d281cc4 | cdn.tsetmc.com | `/api/ClosingPrice/GetTradeTop/MostVisited/{flow}/{top}` | flow, top | json |
| tradetopsalafexpired_a7b871df | cdn.tsetmc.com | `/api/ClosingPrice/GetTradeTop/StandardSalafExpired/{top}/{extra}` | top, extra | json |
| tradetopstandardsalaf_6d87f2c4 | cdn.tsetmc.com | `/api/ClosingPrice/GetTradeTop/StandardSalaf/{top}/{extra}` | top, extra | json |
| tv_config_046ac7f8 | webgw.tse.ir | `/InstrumentProvider/api/v1/TradingView/config` | — | json |
| tv_time_9fc431e2 | webgw.tse.ir | `/InstrumentProvider/api/v1/TradingView/time` | — | text |

## مراجع

هر ردیف JSON، references مستقل دارد. این منابع پیاده‌سازی‌های جامعه توسعه‌دهندگان هستند؛ ادعاهای تست نویسندگان به‌عنوان تست این پروژه گزارش نشده‌اند. عملیات نوشتن حساب کاربری مانند InsertUserConfiguration از این کلاینت بازار کنار گذاشته شده‌اند. SOAP و سرویس دارای اشتراک به قرارداد و احراز هویت جدا نیاز دارند.

- https://github.com/BabakEslami/tse-market-data/blob/main/scripts/test_active_tsetmc_endpoints.py
- https://github.com/BabakEslami/tse-market-data/blob/main/ENDPOINTS.md
- https://github.com/mazaheriMahdi/fis-agent/blob/main/docs/domain/tsetmc-api.md

برای Swagger عمومی و صفحات رسمی نیز تلاش شد؛ سند OpenAPI رسمی قابل بازیابی به دست نیامد. وضعیت‌های source_date_missing، stale_source_date، empty و failed حفظ می‌شوند. کاتالوگ، تضمین قرارداد پایدار سرویس نیست.
