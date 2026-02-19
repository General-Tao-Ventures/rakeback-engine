"""Debug: why is calculated position 356K TAO when actual is ~1.6M TAO?"""

import sys
sys.path.insert(0, "src")

from substrateinterface import SubstrateInterface
from decimal import Decimal

RPC_URL = "ws://185.189.45.20:9944"
HOTKEY = "5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21"
COLDKEY = "5DywxdtESjskgPZrDXL86qV44SpPgJuqs9X6noyJJwX9PaSD"

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

# 1. Check all stake-related storage for this hotkey
print("=== Hotkey-level stake queries ===")
for func in ['TotalStake', 'TotalHotkeyStake', 'Stake', 'TotalColdkeyStake',
             'TotalHotkeyShares']:
    for params in [[HOTKEY], [COLDKEY]]:
        try:
            r = sub.query('SubtensorModule', func, params, block_hash=bh)
            v = xval(r)
            who = "hotkey" if params[0] == HOTKEY else "coldkey"
            if v:
                print(f"  {func}({who}) = {v:,} ({v/1e9:,.4f} TAO)")
        except Exception as e:
            pass

# 2. Check TotalHotkeyShares per subnet
print(f"\n=== TotalHotkeyShares per subnet ===")
total_shares_tao = Decimal(0)
for n in range(0, 128):
    try:
        r = sub.query('SubtensorModule', 'TotalHotkeyShares', [HOTKEY, n], block_hash=bh)
        v = xval(r)
        if v and v > 0:
            # Also get SubnetTAO and TotalHotkeyAlpha for comparison
            alpha_r = sub.query('SubtensorModule', 'TotalHotkeyAlpha', [HOTKEY, n], block_hash=bh)
            alpha_v = xval(alpha_r) or 0

            subnet_tao_r = sub.query('SubtensorModule', 'SubnetTAO', [n], block_hash=bh)
            subnet_tao = xval(subnet_tao_r) or 0

            alpha_out_r = sub.query('SubtensorModule', 'SubnetAlphaOut', [n], block_hash=bh)
            alpha_out = xval(alpha_out_r) or 0

            # Shares might represent TAO value directly
            shares_tao = Decimal(v) / Decimal(1e9)

            # Alpha price
            price = Decimal(subnet_tao) / Decimal(alpha_out) if alpha_out else Decimal(0)
            alpha_tao = Decimal(alpha_v) * price / Decimal(1e9)

            total_shares_tao += shares_tao

            if shares_tao > 100 or alpha_tao > 100:
                print(f"  SN{n}: shares={v:>20,} ({float(shares_tao):>12,.2f} TAO)  alpha={alpha_v:>20,} ({float(alpha_tao):>10,.2f} TAO via price)")
    except:
        pass

print(f"\n  Total from TotalHotkeyShares: {float(total_shares_tao):>14,.2f} TAO")

# 3. Check Alpha storage directly for the coldkey+hotkey
print(f"\n=== Alpha(hotkey) query_map ===")
try:
    alpha_map = sub.query_map('SubtensorModule', 'Alpha', [HOTKEY], block_hash=bh)
    count = 0
    for item in alpha_map:
        count += 1
        if count <= 3:
            print(f"  Sample entry: {item}")
        if count > 10000:
            break
    print(f"  Total Alpha entries: {count}")
except Exception as e:
    print(f"  Error: {e}")

# 4. Check Stake(hotkey, coldkey) - older stake format
print(f"\n=== Stake(hotkey, coldkey) ===")
try:
    r = sub.query('SubtensorModule', 'Stake', [HOTKEY, COLDKEY], block_hash=bh)
    v = xval(r)
    print(f"  Stake(hotkey, coldkey) = {v:,} ({v/1e9:,.4f} TAO)")
except Exception as e:
    print(f"  Error: {e}")

# 5. Check TotalHotkeyAlpha sum vs TotalHotkeyShares sum
print(f"\n=== Summary comparison ===")
total_alpha_tao = Decimal(0)
total_alpha_raw = 0
for n in range(0, 128):
    try:
        alpha_r = sub.query('SubtensorModule', 'TotalHotkeyAlpha', [HOTKEY, n], block_hash=bh)
        alpha_v = xval(alpha_r) or 0
        if alpha_v > 0:
            total_alpha_raw += alpha_v
            subnet_tao_r = sub.query('SubtensorModule', 'SubnetTAO', [n], block_hash=bh)
            subnet_tao = xval(subnet_tao_r) or 0
            alpha_out_r = sub.query('SubtensorModule', 'SubnetAlphaOut', [n], block_hash=bh)
            alpha_out = xval(alpha_out_r) or 0
            price = Decimal(subnet_tao) / Decimal(alpha_out) if alpha_out else Decimal(0)
            total_alpha_tao += Decimal(alpha_v) * price / Decimal(1e9)
    except:
        pass

print(f"  Sum of TotalHotkeyAlpha (raw): {total_alpha_raw:,}")
print(f"  Sum of TotalHotkeyAlpha (TAO): {float(total_alpha_tao):>14,.2f}")
print(f"  Sum of TotalHotkeyShares (TAO): {float(total_shares_tao):>14,.2f}")

# 6. Check OwnedHotkeys for the coldkey
print(f"\n=== OwnedHotkeys for coldkey ===")
try:
    r = sub.query('SubtensorModule', 'OwnedHotkeys', [COLDKEY], block_hash=bh)
    v = r.value if r else None
    if v:
        print(f"  Hotkeys: {v}")
except Exception as e:
    print(f"  Error: {e}")

# 7. StakingHotkeys and StakingColdkeys
print(f"\n=== StakingHotkeys / StakingColdkeys ===")
try:
    r = sub.query('SubtensorModule', 'StakingHotkeys', [COLDKEY], block_hash=bh)
    v = r.value if r else None
    if v:
        print(f"  StakingHotkeys(coldkey): {len(v)} hotkeys")
except Exception as e:
    print(f"  Error: {e}")

try:
    r = sub.query('SubtensorModule', 'StakingColdkeys', [HOTKEY], block_hash=bh)
    v = r.value if r else None
    if v:
        print(f"  StakingColdkeys(hotkey): {len(v)} coldkeys staking to this validator")
except Exception as e:
    print(f"  Error: {e}")

print("\nDone!")
