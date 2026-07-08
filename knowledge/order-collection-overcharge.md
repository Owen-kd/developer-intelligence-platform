---
title: 주문 수집 처리 흐름 & '요금 과충전' 발생 경로
type: root_cause
issues:
code_refs: workResult.ts(setOrder/setBundleCode), order.service.ts:5464(checkNullOrdBundleNo), sol_charge charge_cnt
author: (전문가 작성)
---

## 처리 흐름
주문 수집은 3단계로 처리된다.

1. **주문 저장** — 쇼핑몰 주문을 DB에 저장. `setOrder()` · `workResult.ts`
2. **묶음번호 생성** — 배송 묶음번호 붙이기. `setBundleCode()` · `workResult.ts`
3. **요금 차감** — 수집한 주문 수만큼 차감. `sol_charge charge_cnt+` · line 5356

**핵심 규칙**: 요금은 ②(묶음번호) 다음인 ③에서만 **딱 한 번 차감**된다. → ② 전에 멈추면 요금은 안 깎인다.

## ② '묶음번호 생성' 중 문제가 생기면 (3가지 경우)

- **A. 정상 처리** → 주문 저장됨 · 요금 정상 차감. (정상 완료)
- **B. 처리 중 에러(프로그램 오류)** → catch 에서 저장한 주문을 자동 전체 삭제(`DELETE FROM ord`, line 5384~5415). 주문 없음 · 요금 안 깎임 → 재수집. (문제 없음, 깨끗)
- **C. 서버가 갑자기 다운(OOM 등)** → 자동 삭제를 못 하고 죽음:
  1. **묶음번호 없는 주문이 남음** (`bundle_no = NULL`, 신규주문)
  2. ③(요금 차감) 전에 멈춤 = **요금이 안 깎인 상태**
  3. 나중에 정리: 주문삭제 + 요금 돌려줌. `checkNullOrdBundleNo()` · `order.service.ts:5464`
  4. → **과충전 발생**: 요금 돌려줌(`charge_cnt-`, line 5533) = 공짜 지급

## 근본원인 (결론)
**'묶음번호 없는 주문' = 요금이 아직 안 깎인 주문** (② → ③ 사이에서 끊긴 것).

→ 주문 삭제는 맞지만, **'요금 돌려주기(`charge_cnt-`)'는 안 깎인 걸 돌려주는 과충전이므로 빼야 한다** (수기·자동 모두 해당).
