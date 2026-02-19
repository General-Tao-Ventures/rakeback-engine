"""Cross-check stake values using multiple approaches."""

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

# 1. How many coldkeys stake to this hotkey?
print("=== StakingColdkeys ===")
try:
    r = sub.query('SubtensorModule', 'StakingColdkeys', [HOTKEY], block_hash=bh)
    coldkeys = r.value if r else []
    print(f"  {len(coldkeys)} coldkeys staking to this validator")
except Exception as e:
    print(f"  Error: {e}")
    coldkeys = []

# 2. Check Alpha entries for this hotkey - what do they actually contain?
# Alpha(hotkey, coldkey, netuid) -> amount
print(f"\n=== Alpha storage structure ===")
try:
    # Query a few specific coldkey+netuid combos
    if coldkeys:
        sample_ck = coldkeys[0]
        print(f"  Checking coldkey: {sample_ck}")
        for netuid in [0, 1]:
            try:
                r = sub.query('SubtensorModule', 'Alpha', [HOTKEY, sample_ck, netuid], block_hash=bh)
                v = xval(r)
                print(f"    Alpha(hotkey, coldkey, netuid={netuid}) = {v:,}")
            except Exception as e:
                # Try different param order
                try:
                    r = sub.query('SubtensorModule', 'Alpha', [HOTKEY, netuid, sample_ck], block_hash=bh)
                    v = xval(r)
                    print(f"    Alpha(hotkey, netuid={netuid}, coldkey) = {v:,}")
                except Exception as e2:
                    print(f"    Alpha query failed: {e} / {e2}")
except Exception as e:
    print(f"  Error: {e}")

# 3. TotalStake at network level
print(f"\n=== Network-level stake ===")
try:
    r = sub.query('SubtensorModule', 'TotalStake', block_hash=bh)
    v = xval(r)
    print(f"  TotalStake (network): {v:,} rao = {v/1e9:,.0f} TAO")
except Exception as e:
    print(f"  TotalStake: {e}")

try:
    r = sub.query('SubtensorModule', 'TotalIssuance', block_hash=bh)
    v = xval(r)
    print(f"  TotalIssuance: {v:,} rao = {v/1e9:,.0f} TAO")
except Exception as e:
    print(f"  TotalIssuance: {e}")

# 4. Sanity check: Root (SN0) pool
print(f"\n=== Root pool (SN0) sanity check ===")
subnet_tao_0 = xval(sub.query('SubtensorModule', 'SubnetTAO', [0], block_hash=bh))
alpha_out_0 = xval(sub.query('SubtensorModule', 'SubnetAlphaOut', [0], block_hash=bh))
alpha_in_0 = xval(sub.query('SubtensorModule', 'SubnetAlphaIn', [0], block_hash=bh))
total_alpha_0 = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [HOTKEY, 0], block_hash=bh))
print(f"  SubnetTAO(0):      {subnet_tao_0:,} ({subnet_tao_0/1e9:,.2f} TAO)")
print(f"  SubnetAlphaOut(0): {alpha_out_0:,} ({alpha_out_0/1e9:,.2f})")
print(f"  SubnetAlphaIn(0):  {alpha_in_0:,} ({alpha_in_0/1e9:,.2f})")
print(f"  TotalHotkeyAlpha(validator, 0): {total_alpha_0:,} ({total_alpha_0/1e9:,.2f})")
if alpha_out_0:
    price_0 = subnet_tao_0 / alpha_out_0
    val_0 = total_alpha_0 * price_0 / 1e9
    print(f"  Price: {price_0:.6f}")
    print(f"  Validator root TAO value: {val_0:,.2f}")
    share_0 = total_alpha_0 / alpha_out_0 * 100
    print(f"  Validator share of root pool: {share_0:.2f}%")
    print(f"  If share applies to SubnetTAO: {subnet_tao_0/1e9 * share_0/100:,.2f} TAO")

# 5. Check total across ALL subnets with detailed breakdown
print(f"\n=== Full alpha → TAO breakdown (all subnets) ===")
total_tao_value = Decimal(0)
subnet_details = []
for n in range(0, 128):
    try:
        alpha = xval(sub.query('SubtensorModule', 'TotalHotkeyAlpha', [HOTKEY, n], block_hash=bh))
        if not alpha or alpha <= 0:
            continue
        s_tao = xval(sub.query('SubtensorModule', 'SubnetTAO', [n], block_hash=bh)) or 1
        s_alpha = xval(sub.query('SubtensorModule', 'SubnetAlphaOut', [n], block_hash=bh)) or 1
        price = Decimal(s_tao) / Decimal(s_alpha)
        tao_val = Decimal(alpha) * price / Decimal(1e9)
        total_tao_value += tao_val
        subnet_details.append((n, alpha, s_tao, s_alpha, float(price), float(tao_val)))
    except:
        pass

# Sort by TAO value
subnet_details.sort(key=lambda x: x[5], reverse=True)

# Show top 10 subnets
for n, alpha, s_tao, s_alpha, price, tao_val in subnet_details[:10]:
    pct = alpha / s_alpha * 100
    print(f"  SN{n:>3}: alpha={alpha/1e9:>14,.2f}  price={price:.8f}  TAO_val={tao_val:>12,.2f}  pool_share={pct:.2f}%")

print(f"  ...")
print(f"  SUM across {len(subnet_details)} subnets: {float(total_tao_value):>14,.2f} TAO")

# 6. What if TotalHotkeyAlpha is NOT in rao? What if it's in a smaller unit?
print(f"\n=== Unit check ===")
print(f"  If alpha is in rao (1e-9), total = {float(total_tao_value):,.2f} TAO")
print(f"  If alpha is in planck (1e-12), total = {float(total_tao_value * 1000):,.2f} TAO")
print(f"  If alpha is in 1e-18, total = {float(total_tao_value * 1e9):,.2f} TAO")

# 7. Check if there's a separate RootProp or claim mechanism
print(f"\n=== RootProp / RootClaimable ===")
for func in ['RootProp', 'RootClaimable']:
    try:
        r = sub.query('SubtensorModule', func, [HOTKEY], block_hash=bh)
        v = xval(r)
        print(f"  {func}(hotkey) = {v}")
    except Exception as e:
        print(f"  {func}: {e}")

# 8. Look at Delegates map entry for our hotkey
print(f"\n=== Delegates ===")
r = sub.query('SubtensorModule', 'Delegates', [HOTKEY], block_hash=bh)
v = xval(r)
take_pct = v / 65535 * 100 if v else 0
print(f"  Delegates(hotkey) = {v} ({take_pct:.2f}%)")

# 9. Check NumStakingColdkeys for context
print(f"\n=== Network staking stats ===")
try:
    r = sub.query('SubtensorModule', 'NumStakingColdkeys', block_hash=bh)
    v = xval(r)
    print(f"  NumStakingColdkeys: {v:,}")
except Exception as e:
    print(f"  NumStakingColdkeys: {e}")

# 10. Let's check TaoStats API for comparison
print(f"\n=== TaoStats cross-check ===")
try:
    import urllib.request, json
    req = urllib.request.Request(
        f"https://api.taostats.io/api/v1/validator/{HOTKEY}",
        headers={"Accept": "application/json", "User-Agent": "RakebackEngine/1.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        if isinstance(data, dict):
            for k in ['total_stake', 'stake', 'nominators', 'total_daily_return']:
                if k in data:
                    print(f"  {k}: {data[k]}")
        print(f"  Full keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
except Exception as e:
    print(f"  TaoStats API: {e}")

print("\nDone!")
