---
title: 주문 수집 처리 흐름 & '교환주문 플래그' 노출 경로
type: root_cause
issues:
code_refs: order-excel.service.ts:923, calculate.service.ts:1374, workResult.ts(몰별 케이스), config/shop.ts:29(sendDelivNo.exchangeOrd)
author: (전문가 작성)
---

## 처리 흐름
1. **주문 수집** — 쇼핑몰 API 응답 수신. `exchange_ord_collect_yn` 확인
2. **교환주문 판정** — 교환건이면 플래그 세팅. `exchange_ord_yn = 1`
3. **원주문 연결** — 원주문 uniq 매칭. `ori_uniq = 원주문 uniq`
4. **플래그 노출** — 주문 목록/엑셀 화면에 '교환' 뱃지 표시

**핵심 규칙**: 플래그 노출 조건 = `ori_uniq` 있음 **AND** `exchange_ord_yn = 1` — 둘 다 만족해야 노출됨.

## '플래그 미노출'이 발생하는 4가지 경로

- **A. 계정 설정 OFF** — 쇼핑몰 계정 설정에서 교환주문 수집이 꺼져 있음(`sol_shop.exchange_ord_collect_yn = 0`). 수집 단계부터 교환건을 아예 처리 안 함 → 플래그 세팅 안 됨. **해결**: 쇼핑몰 계정 설정에서 교환주문 수집 활성화.
- **B. 쇼핑몰 미지원** — 해당 쇼핑몰 API가 교환주문 정보를 제공하지 않음. PA5 엔진이 교환건 자체를 수집 못 함(`exchange_ord_yn` 세팅 불가). **해결**: 쇼핑몰 정책 확인, PA5 엔진 지원 여부 확인.
- **C. 원주문 미매칭** — 교환건은 인식했으나 원주문 uniq를 우리 시스템에서 못 찾음(`ori_uniq = NULL`). `exchange_ord_yn=1` 이지만 `ori_uniq` 없어 노출 조건 불성립. **해결**: 원주문이 우리 시스템에 존재하는지 확인(주문 수집 기간 등).
- **D. 특정 몰 예외** — 몰별 특별 처리 로직 존재(예: 롯데 A076). `pa_shop_cd === 'A076' && exchange_ord_yn == 1`. `workResult.ts` 등에서 몰별 조건 분기 → 케이스별 결과 상이. **해결**: 해당 몰 처리 로직 개별 확인.

## 근본원인 (결론)
**플래그 미노출 = `ori_uniq` 없음 또는 `exchange_ord_yn = 0`.**

- 노출 조건 검증 위치: `order-excel.service.ts:923`, `calculate.service.ts:1374`
- 미노출 주문 발견 시 확인 순서: ① 계정 설정 → ② 몰 지원 여부 → ③ 원주문 존재 → ④ 몰별 예외 처리

## 교환재발송 지원 몰 안내
- **지원(수집 O)**: `shop.exchange_ord_collect_yn = 1` 인 쇼핑몰 (쇼핑몰별 DB에 개별 설정, 계정 등록 시 자동 결정). 조회: `SELECT shop_cd, shop_name FROM shop WHERE exchange_ord_collect_yn = 1;`
- **송장 전송까지 지원**: 하드코딩 리스트 포함 몰만 교환주문 송장전송 가능. `config/shop.ts:29` `sendDelivNo.exchangeOrd`. 예: **A524 SSG**(추가처리).
- **특별 처리 몰**: 교환주문 처리를 별도 로직으로 분기. `workResult.ts` 몰별 케이스. 예: **A076 롯데**(`exchange_ord_yn` 별도 매칭 로직).
- **지원 불가**: 자체 몰 또는 API 미제공 몰은 교환주문 수집·송장 전송 모두 불가. 예: **A000 자체 몰**.
