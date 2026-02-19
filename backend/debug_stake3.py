"""Test different price formulas to find which matches ~1.6M TAO."""

import sys
sys.path.insert(0, "src")

from substrateinterface import SubstrateInterface
from decimal import Decimal

RPC_URL = "ws://185.189.45.20:9944"
HOTKEY = "5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21"

def xval(result):
    if result is None: return 0
    v = result.value if hasattr(result, 'value') else result
    if v is None: return 0
    if isinstance(v, dict) and 'bits' in v: return v['bits']
    return v

sub = SubstrateInterface(url=RPC_URL, ss58_format=42, auto_discover=True, auto_reconnect=True)
head = sub.get_block()['header']['number'] - 2
bh = sub.get_block_hash(head)
print(f"Block: {head}\n")

# Collect data for all active subnets
subnets = []
for n in range(0, 128):
    try:
        alpha = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [HOTKEY, n], block_hash=bh))
        if not alpha or alpha <= 0:
            continue
        s_tao = xval(sub.query('SubtensorModule', 'SubnetTAO', [n], block_hash=bh)) or 0
        s_alpha_out = xval(sub.query('SubtensorModule', 'SubnetAlphaOut', [n], block_hash=bh)) or 0
        s_alpha_in = xval(sub.query('SubtensorModule', 'SubnetAlphaIn', [n], block_hash=bh)) or 0
        subnets.append((n, alpha, s_tao, s_alpha_out, s_alpha_in))
    except:
        pass

print(f"Active subnets: {len(subnets)}\n")

# Method A: price = SubnetTAO / SubnetAlphaOut
total_a = Decimal(0)
for n, alpha, s_tao, s_out, s_in in subnets:
    price = Decimal(s_tao) / Decimal(s_out) if s_out else Decimal(0)
    total_a += Decimal(alpha) * price / Decimal(10**9)

# Method B: price = SubnetTAO / SubnetAlphaIn  (AMM spot price)
total_b = Decimal(0)
for n, alpha, s_tao, s_out, s_in in subnets:
    price = Decimal(s_tao) / Decimal(s_in) if s_in else Decimal(0)
    total_b += Decimal(alpha) * price / Decimal(10**9)

# Method C: price = SubnetTAO / (SubnetAlphaIn + SubnetAlphaOut) — total alpha supply
total_c = Decimal(0)
for n, alpha, s_tao, s_out, s_in in subnets:
    total_supply = s_in + s_out
    price = Decimal(s_tao) / Decimal(total_supply) if total_supply else Decimal(0)
    total_c += Decimal(alpha) * price / Decimal(10**9)

print(f"Method A (TAO/AlphaOut):              {float(total_a):>14,.2f} TAO")
print(f"Method B (TAO/AlphaIn — AMM spot):    {float(total_b):>14,.2f} TAO")
print(f"Method C (TAO/(AlphaIn+AlphaOut)):    {float(total_c):>14,.2f} TAO")

# Show breakdown for top subnets under Method B
print(f"\n{'─'*80}")
print(f"Method B breakdown (TAO/AlphaIn — AMM spot price):")
print(f"{'SN':>4} {'Alpha':>16} {'SubnetTAO':>16} {'AlphaIn':>16} {'Price':>12} {'TAO Value':>14}")
print(f"{'─'*80}")

details = []
for n, alpha, s_tao, s_out, s_in in subnets:
    price = Decimal(s_tao) / Decimal(s_in) if s_in else Decimal(0)
    tao_val = Decimal(alpha) * price / Decimal(10**9)
    details.append((n, alpha, s_tao, s_in, float(price), float(tao_val)))

details.sort(key=lambda x: x[5], reverse=True)
for n, alpha, s_tao, s_in, price, tao_val in details[:15]:
    print(f"SN{n:>3} {alpha/1e9:>16,.2f} {s_tao/1e9:>16,.2f} {s_in/1e9:>16,.2f} {price:>12.6f} {tao_val:>14,.2f}")

print(f"{'─'*80}")
print(f"{'TOTAL':>53} {float(total_b):>14,.2f}")

# Also check: what does the emission revenue look like under Method B pricing?
print(f"\n{'='*80}")
print(f"Revenue recalc under Method B pricing:")
total_rev = Decimal(0)
rev_details = []
for n, alpha, s_tao, s_out, s_in in subnets:
    try:
        tempo = xval(sub.query('SubtensorModule', 'Tempo', [n], block_hash=bh)) or 360
        last_step = xval(sub.query('SubtensorModule', 'LastMechansimStepBlock', [n], block_hash=bh))
        if not last_step:
            continue
        sh = sub.get_block_hash(last_step)
        ph = sub.get_block_hash(last_step - 1)
        c = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [HOTKEY, n], block_hash=sh))
        p = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [HOTKEY, n], block_hash=ph))
        emission = c - p
        if emission <= 0:
            continue
        price = Decimal(s_tao) / Decimal(s_in) if s_in else Decimal(0)
        tao_epoch = Decimal(emission) * price / Decimal(10**9)
        epochs_day = Decimal(86400) / Decimal(tempo * 12)
        tao_day = tao_epoch * epochs_day
        total_rev += tao_day
        rev_details.append((n, emission, float(price), float(tao_day)))
    except:
        pass

rev_details.sort(key=lambda x: x[3], reverse=True)
for n, em, price, tao_day in rev_details[:10]:
    print(f"  SN{n:>3}: {tao_day:>12,.4f} TAO/day")
print(f"  TOTAL: {float(total_rev):>12,.4f} TAO/day = {float(total_rev)*365:>12,.2f} TAO/year")

print("\nDone!")
