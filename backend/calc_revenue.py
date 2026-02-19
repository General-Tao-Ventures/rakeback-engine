"""Calculate gross revenue for the validator across all subnets."""

import sys
sys.path.insert(0, "src")

from substrateinterface import SubstrateInterface
from decimal import Decimal

RPC_URL = "ws://185.189.45.20:9944"
VALIDATOR = "5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21"
BLOCK_TIME = 12  # seconds


def xval(result):
    """Extract numeric value from substrate query, handling {'bits': N} dicts."""
    if result is None:
        return 0
    v = result.value if hasattr(result, 'value') else result
    if v is None:
        return 0
    if isinstance(v, dict) and 'bits' in v:
        return v['bits']
    return v


print(f"Connecting to {RPC_URL}...")
sub = SubstrateInterface(url=RPC_URL, ss58_format=42, auto_discover=True, auto_reconnect=True)

head_num = sub.get_block()['header']['number'] - 2
bh = sub.get_block_hash(head_num)
print(f"Block: {head_num}")

# ── Discover active subnets ─────────────────────────────────────────
active = []
for n in range(0, 128):
    try:
        a = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [VALIDATOR, n], block_hash=bh))
        if a > 0:
            active.append(n)
    except:
        pass

# Delegate take
take_raw = xval(sub.query('SubtensorModule', 'Delegates', [VALIDATOR], block_hash=bh))
take_pct = (take_raw / 65535) * 100 if take_raw else 0

print(f"\n{'='*75}")
print(f" VALIDATOR RT21 — {VALIDATOR[:20]}...")
print(f" Active subnets: {len(active)} | Delegate Take: {take_pct:.1f}%")
print(f"{'='*75}")

# ── Per-subnet data ─────────────────────────────────────────────────
rows = []
for n in active:
    try:
        tempo = xval(sub.query('SubtensorModule', 'Tempo', [n], block_hash=bh)) or 360
        last_step = xval(sub.query('SubtensorModule', 'LastMechansimStepBlock', [n], block_hash=bh))
        total_alpha = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [VALIDATOR, n], block_hash=bh))
        subnet_tao = xval(sub.query('SubtensorModule', 'SubnetTAO', [n], block_hash=bh))
        alpha_in = xval(sub.query('SubtensorModule', 'SubnetAlphaIn', [n], block_hash=bh))

        # Token symbol
        sym_raw = xval(sub.query('SubtensorModule', 'TokenSymbol', [n], block_hash=bh))
        sym = ""
        if isinstance(sym_raw, int) and sym_raw > 0:
            try:
                sym = sym_raw.to_bytes((sym_raw.bit_length() + 7) // 8, 'big').decode('utf-8', errors='ignore').strip('\x00')
            except:
                pass
        if not sym:
            sym = f"SN{n}"

        # Emission at last tempo step: delta in TotalHotkeyAlpha
        emission = 0
        if last_step > 0:
            try:
                sh = sub.get_block_hash(last_step)
                ph = sub.get_block_hash(last_step - 1)
                c = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [VALIDATOR, n], block_hash=sh))
                p = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [VALIDATOR, n], block_hash=ph))
                emission = c - p
            except:
                pass

        # AMM spot price: TAO_rao per alpha_rao = SubnetTAO / SubnetAlphaIn
        price = Decimal(subnet_tao) / Decimal(alpha_in) if alpha_in else Decimal(0)

        # TAO value of emission: emission_rao * price / 1e9
        tao_per_epoch = Decimal(emission) * price / Decimal(1e9) if emission > 0 else Decimal(0)

        epochs_per_day = Decimal(86400) / Decimal(tempo * BLOCK_TIME)
        tao_daily = tao_per_epoch * epochs_per_day

        rows.append({
            'n': n, 'sym': sym, 'tempo': tempo,
            'total_alpha': total_alpha, 'emission': emission,
            'price': price, 'subnet_tao_total': subnet_tao,
            'alpha_in': alpha_in,
            'tao_epoch': tao_per_epoch, 'tao_daily': tao_daily,
            'validator_alpha': total_alpha,
        })
    except Exception as e:
        print(f"  SN{n}: error — {e}")

# Sort by daily TAO descending
rows.sort(key=lambda r: r['tao_daily'], reverse=True)

# ── Table ────────────────────────────────────────────────────────────
print(f"\n{'SN':<5}{'Sym':<6}{'Tmp':>4} {'α Emission/Epoch':>18} {'α→τ Price':>12} {'τ/Epoch':>12} {'τ/Day':>12} {'Stk Share':>10}")
print(f"{'─'*82}")

total_daily = Decimal(0)
for r in rows:
    if r['emission'] <= 0:
        continue
    total_daily += r['tao_daily']
    share = r['total_alpha'] / r['alpha_in'] * 100 if r['alpha_in'] else 0
    print(f"SN{r['n']:<3}{r['sym']:<6}{r['tempo']:>4} {r['emission']:>18,} {float(r['price']):>12.8f} {float(r['tao_epoch']):>12.4f} {float(r['tao_daily']):>12.4f} {float(share):>9.2f}%")

total_monthly = total_daily * 30
total_yearly = total_daily * 365

# Also compute total alpha position value in TAO
total_alpha_tao_value = Decimal(0)
for r in rows:
    alpha_tao = Decimal(r['total_alpha']) * r['price'] / Decimal(1e9)
    total_alpha_tao_value += alpha_tao

# ── Summary ──────────────────────────────────────────────────────────
print(f"\n{'='*75}")
print(f" GROSS REVENUE (all emissions to delegators, pre-take)")
print(f"{'='*75}")
print(f"  Daily:    {float(total_daily):>14,.4f} TAO")
print(f"  Monthly:  {float(total_monthly):>14,.4f} TAO")
print(f"  Yearly:   {float(total_yearly):>14,.2f} TAO")

val_daily = total_daily * Decimal(take_pct) / 100
val_monthly = val_daily * 30
val_yearly = val_daily * 365

del_daily = total_daily - val_daily
del_monthly = del_daily * 30
del_yearly = del_daily * 365

print(f"\n  VALIDATOR TAKE ({take_pct:.1f}%):")
print(f"    Daily:    {float(val_daily):>14,.4f} TAO")
print(f"    Monthly:  {float(val_monthly):>14,.4f} TAO")
print(f"    Yearly:   {float(val_yearly):>14,.2f} TAO")

print(f"\n  NET TO DELEGATORS ({100-take_pct:.1f}%):")
print(f"    Daily:    {float(del_daily):>14,.4f} TAO")
print(f"    Monthly:  {float(del_monthly):>14,.4f} TAO")
print(f"    Yearly:   {float(del_yearly):>14,.2f} TAO")

print(f"\n  TOTAL ALPHA POSITION VALUE: {float(total_alpha_tao_value):>14,.2f} TAO")

# ── USD conversion ───────────────────────────────────────────────────
try:
    import urllib.request, json
    req = urllib.request.Request(
        "https://api.coingecko.com/api/v3/simple/price?ids=bittensor&vs_currencies=usd",
        headers={"Accept": "application/json", "User-Agent": "RakebackEngine/1.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        tao_usd = json.loads(resp.read()).get("bittensor", {}).get("usd", 0)
except:
    tao_usd = 0

if tao_usd:
    print(f"\n{'─'*75}")
    print(f"  TAO/USD: ${tao_usd:,.2f}")
    print(f"\n  USD GROSS REVENUE:")
    print(f"    Daily:    ${float(total_daily) * tao_usd:>14,.2f}")
    print(f"    Monthly:  ${float(total_monthly) * tao_usd:>14,.2f}")
    print(f"    Yearly:   ${float(total_yearly) * tao_usd:>14,.2f}")
    print(f"\n  USD VALIDATOR TAKE ({take_pct:.1f}%):")
    print(f"    Daily:    ${float(val_daily) * tao_usd:>14,.2f}")
    print(f"    Monthly:  ${float(val_monthly) * tao_usd:>14,.2f}")
    print(f"    Yearly:   ${float(val_yearly) * tao_usd:>14,.2f}")
    print(f"\n  USD NET TO DELEGATORS:")
    print(f"    Daily:    ${float(del_daily) * tao_usd:>14,.2f}")
    print(f"    Monthly:  ${float(del_monthly) * tao_usd:>14,.2f}")
    print(f"    Yearly:   ${float(del_yearly) * tao_usd:>14,.2f}")
    print(f"\n  TOTAL ALPHA POSITION: ${float(total_alpha_tao_value) * tao_usd:>14,.2f}")

# ── Top 10 subnets detail ───────────────────────────────────────────
top = [r for r in rows if r['emission'] > 0][:10]
print(f"\n{'='*75}")
print(f" TOP 10 SUBNETS BY DAILY REVENUE")
print(f"{'='*75}")
for i, r in enumerate(top, 1):
    alpha_tao = Decimal(r['total_alpha']) * r['price'] / Decimal(1e9)
    alpha_pct = r['total_alpha'] / r['alpha_in'] * 100 if r['alpha_in'] else 0
    print(f"\n  {i}. SN{r['n']} ({r['sym']})")
    print(f"     Emission:  {r['emission']:>18,} alpha/epoch × {float(Decimal(86400)/Decimal(r['tempo']*BLOCK_TIME)):.1f} epochs/day")
    print(f"     Price:     {float(r['price']):.8f} TAO/alpha  ({r['subnet_tao_total']/1e9:,.0f} TAO locked)")
    print(f"     Revenue:   {float(r['tao_daily']):>12,.4f} TAO/day" + (f" = ${float(r['tao_daily'])*tao_usd:>10,.2f}/day" if tao_usd else ""))
    print(f"     Position:  {r['total_alpha']/1e9:>12,.2f} alpha ({float(alpha_pct):.2f}% of subnet) = {float(alpha_tao):>10,.2f} TAO")

print(f"\n{'='*75}")
print("Done!")
