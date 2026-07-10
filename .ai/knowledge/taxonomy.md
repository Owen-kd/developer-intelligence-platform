# 지식 택소노미 — 이슈 Facet 분류 체계

> 오너 지시(2026-07-10): "이슈를 그냥 저장하지 말고, 어떤 내용에 속하는지 먼저 자른다. 구조를 먼저 잡는다."
> **근거**: 어휘를 지어내지 않고 백엔드 실 도메인 문서(`gmp.openapi.2023/.ai`)에 정렬한다 —
> `context/domain-map.md`(도메인 레지스트리) · `context/glossary.md`(마켓코드·용어) · `domains/product/overview.md`(기능영역).
> 결정: 단일 트리 ❌ → **직교 facet** ✅. 상태: **확정(Accepted)** — [ADR-015](../decisions/ADR-015-issue-faceted-taxonomy.md) 오너 승인 2026-07-10.

## 핵심 통찰 (문서에서 배운 것)
백엔드는 이미 **`도메인 → 기능영역 → 액션`** 3단 계층 + 직교 축(채널·유형)으로 사고한다.
Jira `components`(`상품-오류-툴`)는 이 구조를 문자열에 압축한 것 → **분해해서 축으로 복원**한다.
이슈 하나가 여러 축에 동시에 걸리므로(PA20-19864 = 상품·매칭/옵션·수정·오류·쿠팡·엔진) 단일 트리가 아니라 facet.

## Facet 축 (통제 어휘 = 코드 기반)
각 이슈 = 축마다 값 1개(없으면 `공통`/`미상`).

### ① 도메인 (domain) — 대분류 · `domain-map.md` 레지스트리
`product(상품)` / `order(주문)` / `stock(재고)` / `pay(결제)` / `calculate(정산)` / `inquiry-as(문의·AS)` /
`work(작업)` / `settings(설정)` / `user(회원)` / `shop(쇼핑몰계정)` / `auto-match(자동매칭)` /
`stats(통계)` / `history(이력)` / `promotion` / `notice` / `memo` / `msg(알림)` / `common(공통)` / `기타`
> 소유권 주의(문서): 마스터상품 `prod` CRUD 는 **stock** 소유, product 는 read. 매칭은 product/auto-match.

### ② 기능영역 (feature-area) — 중분류 · 도메인별 하위 모듈
도메인 안의 기능 묶음. **product 확정본**(overview.md 컨트롤러/서비스 기준):
`online(온라인상품 등록·수정·삭제·조회)` / `matching(SKU매칭·수집상품)` / `category(카테고리)` /
`template(등록템플릿)` / `setinfo(추가항목)` / `add-option(추가구매옵션)` / `addcontent(머리말·꼬리말)` /
`noti(상품정보제공고시)` / `keyword-ai(AI키워드·상품명)` / `excel(엑셀 일괄)` / `scrap(수집·자동세팅)` / `option(옵션·옵션관리코드)`
> order/stock/work 등은 도메인 문서가 아직 TODO → 부트스트랩 후 확장(초기엔 `미상` 허용).

### ③ 액션 (action) — 소분류 · `overview.md` §5 플로우
`등록(add)` / `수정(edit)` / `삭제(delete)` / `조회(detail)` / `복사(copy)` / `일괄수정(batch)` /
`매칭(match)` / `매칭해제(cancel)` / `자동매칭(auto-match)` / `수집(scrap)` / `자동세팅(auto-setting)` /
`상태변경(status)` / `동기화(sync)` / `연동(link)` / `정책(policy)`

### ④ 채널 (channel) — 직교 · `glossary.md` §2 마켓코드
`쿠팡(B378)` / `옥션(A001)` / `지마켓(A006)` / `ESM(옥션+지마켓)` / `스마트스토어(A077)` / `11번가(A112)` /
`SSG(A032)` / `인터파크(A027)` / `위메프(B719)` / `홈플러스(B502)` / `카카오톡스토어(B688)` / `아임웹(B005)` /
`Qoo10` / `GSSHOP` / `더현대` / `이지웰몰` / `마스터(Z000)` / `공통`
> ESM 은 옥션+지마켓 통합(`ebay_shop_mas_no`). 마스터(Z000)는 실마켓 아닌 원본 상품.

### ⑤ 유형 (type) — 직교 · Jira component 토큰
`오류(bug)` / `기능개선(enhancement)` / `문의(inquiry)` / `정책(policy)`  — 규칙 자동 ~100%

### ⑥ 팀·영역 (team/area) — 직교
`팀`: 툴(PA20, 솔루션 백엔드) / 엔진(ENG, PA5) — 키 prefix 100%.
`영역`: 엔진(PA5) / 툴(솔루션) / 백오피스 / 미상 — component 접미사(`-엔진`/`-툴`).
> 팀 ≠ 영역: 팀=접수·담당, 영역=영향받는 시스템. PA5=외부 마켓 통신 위임 엔진(glossary §2.4).

## 둘러보기 계층 (대분류 > 중분류 > 소분류)
기본 경로: **도메인 > 기능영역 > 액션**. 채널·유형·팀은 필터.
- 예) PA20-19864 → `상품 > 매칭/옵션 > 수정` (필터: 오류·쿠팡·엔진)
- 예) PA20-18841 → `상품 > 온라인 > 수정` (필터: 쿠팡)
> 당신 예시 `상품>쇼핑몰>쿠팡>수정`도 여전히 성립(채널을 경로에 넣은 뷰). facet이라 뷰를 자유 조합.

## 배정 파이프라인 (승인 시 구현안)
1. **규칙 부트스트랩**(LLM 0): component/label/prefix → 유형·팀·영역·(가능시)도메인·채널. `상품-오류-툴`에 다 있음.
2. **LLM 보강**(고정 어휘 제한): 규칙으로 못 채운 축(주로 기능영역·액션·문의성 도메인)만 "이 목록 중 하나". 스키마 검증·`미상` 폴백.
3. **이벤트화**: `IssueClassified` + 분류 저장(원본 불변, 재분류=새 버전).
4. **활용**: 검색 facet 필터 · 접근제어 서가(도메인/팀) · Obsidian facet 폴더·태그 · gap "빈 분류" · Graphify 씨앗.

## 열린 질문 (승인 시 확정)
- 기능영역 어휘: product 확정 · order/stock/work 는 백엔드 문서 진행 따라 확장(지금은 product만 완결).
- 액션에 도메인특화(매칭/자동세팅) vs 범용(등록/수정) 혼재 OK? — 초안은 혼재 허용.
- 저장 형태: `issue_facets` 테이블(정규화·인덱스 유리, 추천) vs `issues.facets` jsonb.
- 소유권 반영(prod=stock 소유)을 분류에 강제할지 vs 표면 도메인 우선.
