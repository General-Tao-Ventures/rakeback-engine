import { useState } from "react";
import { StatusBadge, StatusType } from "../components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Button } from "../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
import {
  Plus,
  Edit,
  Shield,
  History,
  AlertTriangle,
  Info,
  CheckCircle,
} from "lucide-react";
import { toast } from "sonner";
import { useBlockchain } from "../../hooks/use-blockchain";

interface Partner {
  id: string;
  name: string;
  type: "Named" | "Tag-based" | "Hybrid";
  rakebackRate: number;
  priority: number;
  status: StatusType;
  createdBy: string;
  createdDate: string;
  walletAddress?: string;
  memoTag?: string;
  applyFromDate?: string;
}

interface EligibilityRule {
  id: string;
  partnerId: string;
  type: "wallet" | "memo" | "subnet-filter";
  config: any;
  appliesFromBlock: number;
  createdAt: string;
  createdBy: string;
}

interface RuleChangeLogEntry {
  timestamp: string;
  user: string;
  action: string;
  partner: string;
  details: string;
  appliesFromBlock: number;
}

const mockPartners: Partner[] = [
  {
    id: "partner-creative-builds",
    name: "Creative Builds",
    type: "Named",
    rakebackRate: 15,
    priority: 1,
    status: "active",
    createdBy: "sean@localhost",
    createdDate: "2025-11-15",
    walletAddress: "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL",
  },
  {
    id: "partner-talisman",
    name: "Talisman",
    type: "Tag-based",
    rakebackRate: 12,
    priority: 2,
    status: "active",
    createdBy: "sean@localhost",
    createdDate: "2025-11-20",
    memoTag: "talisman",
  },
];

const mockRules: Record<string, EligibilityRule[]> = {
  "partner-creative-builds": [
    {
      id: "rule-cb-wallet-1",
      partnerId: "partner-creative-builds",
      type: "wallet",
      config: {
        wallet: "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL",
        label: "Creative Builds custody wallet",
      },
      appliesFromBlock: 4200000,
      createdAt: "2025-11-15 10:00:00",
      createdBy: "sean@localhost",
    },
  ],
  "partner-talisman": [
    {
      id: "rule-tl-memo-1",
      partnerId: "partner-talisman",
      type: "memo",
      config: {
        memoString: "talisman",
        matchType: "contains",
        extrinsicTypes: ["stake", "unstake", "redelegate"],
      },
      appliesFromBlock: 4250000,
      createdAt: "2025-11-20 14:30:00",
      createdBy: "sean@localhost",
    },
  ],
};

const initialRuleChangeLog: RuleChangeLogEntry[] = [
  {
    timestamp: "2026-01-15 09:23:00",
    user: "sean@localhost",
    action: "Updated rakeback rate",
    partner: "Creative Builds",
    details: "15% → 15% (no change to rate, priority updated)",
    appliesFromBlock: 4400000,
  },
  {
    timestamp: "2025-12-01 11:45:00",
    user: "sean@localhost",
    action: "Added wallet rule",
    partner: "Creative Builds",
    details: "Added wallet: 5CiP...2DjL",
    appliesFromBlock: 4350000,
  },
  {
    timestamp: "2025-11-20 14:30:00",
    user: "sean@localhost",
    action: "Created partner",
    partner: "Talisman",
    details: "Tag-based partner with memo matching",
    appliesFromBlock: 4250000,
  },
  {
    timestamp: "2025-11-15 10:00:00",
    user: "sean@localhost",
    action: "Created partner",
    partner: "Creative Builds",
    details: "Named partner with custody wallet",
    appliesFromBlock: 4200000,
  },
];

export default function PartnerManagement() {
  const blockchain = useBlockchain();
  const [selectedPartner, setSelectedPartner] = useState<string | null>(null);
  const [showRulesDialog, setShowRulesDialog] = useState(false);
  const [showAddPartnerDialog, setShowAddPartnerDialog] = useState(false);
  const [newRuleType, setNewRuleType] = useState<string>("wallet");
  const [newPartnerType, setNewPartnerType] = useState<string>("named");
  const [partners, setPartners] = useState<Partner[]>(mockPartners);
  const [ruleChangeLog, setRuleChangeLog] = useState<RuleChangeLogEntry[]>(initialRuleChangeLog);

  // Form fields for new partner
  const [partnerName, setPartnerName] = useState("");
  const [rakebackRate, setRakebackRate] = useState("");
  const [priority, setPriority] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [walletLabel, setWalletLabel] = useState("");
  const [memoKeyword, setMemoKeyword] = useState("");
  const [matchType, setMatchType] = useState("contains");
  const [hybridWallet, setHybridWallet] = useState("");
  const [hybridWalletLabel, setHybridWalletLabel] = useState("");
  const [hybridMemo, setHybridMemo] = useState("");
  const [hybridMatchType, setHybridMatchType] = useState("contains");
  const [applyFromDate, setApplyFromDate] = useState("");
  const [applyFromBlock, setApplyFromBlock] = useState("");

  // Helper function to add log entry
  const addLogEntry = (entry: Omit<RuleChangeLogEntry, "timestamp" | "user">) => {
    const newEntry: RuleChangeLogEntry = {
      ...entry,
      timestamp: new Date().toISOString().replace("T", " ").slice(0, 19),
      user: "sean@localhost", // In production, get from auth context
    };
    setRuleChangeLog([newEntry, ...ruleChangeLog]);
  };

  const handleEditRules = (partnerId: string) => {
    setSelectedPartner(partnerId);
    setShowRulesDialog(true);
  };

  const handleAddPartner = () => {
    setShowAddPartnerDialog(true);
    // Reset form fields
    setPartnerName("");
    setRakebackRate("");
    setPriority("");
    setWalletAddress("");
    setWalletLabel("");
    setMemoKeyword("");
    setMatchType("contains");
    setHybridWallet("");
    setHybridWalletLabel("");
    setHybridMemo("");
    setHybridMatchType("contains");
    setApplyFromDate("");
    setApplyFromBlock("");
  };

  const handleSavePartner = () => {
    // Validate required fields
    if (!partnerName || !rakebackRate || !priority) {
      toast.error("Please fill in all required fields");
      return;
    }

    // Determine apply from block (use blockchain current block + 10 as default)
    const currentBlock = blockchain.currentBlock || 4527342;
    const effectiveBlock = applyFromBlock 
      ? parseInt(applyFromBlock) 
      : currentBlock + 10;

    // Create new partner
    const newPartner: Partner = {
      id: `partner-${partnerName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}`,
      name: partnerName,
      type:
        newPartnerType === "named"
          ? "Named"
          : newPartnerType === "tag-based"
          ? "Tag-based"
          : "Hybrid",
      rakebackRate: parseFloat(rakebackRate),
      priority: parseInt(priority),
      status: "active",
      createdBy: "sean@localhost",
      createdDate: new Date().toISOString().split("T")[0],
      walletAddress: newPartnerType === "named" ? walletAddress : undefined,
      memoTag: newPartnerType === "tag-based" ? memoKeyword : undefined,
      applyFromDate: applyFromBlock
        ? undefined
        : applyFromDate
        ? applyFromDate
        : undefined,
    };

    // Add to partners list
    setPartners([...partners, newPartner]);

    // Build details string
    let details = "";
    if (newPartnerType === "named") {
      details = `Named partner with wallet ${walletAddress.slice(0, 8)}...${walletAddress.slice(-8)} at ${rakebackRate}% rakeback`;
    } else if (newPartnerType === "tag-based") {
      details = `Tag-based partner with memo "${memoKeyword}" at ${rakebackRate}% rakeback`;
    } else {
      details = `Hybrid partner with multiple rules at ${rakebackRate}% rakeback`;
    }

    // Add log entry for partner creation
    addLogEntry({
      action: "Created partner",
      partner: partnerName,
      details: details,
      appliesFromBlock: effectiveBlock,
    });

    // Show success message with details
    const blockInfo = applyFromBlock
      ? `from block ${applyFromBlock}`
      : applyFromDate
      ? `from date ${applyFromDate}`
      : `from block ${effectiveBlock}`;

    toast.success(
      `Partner "${partnerName}" created successfully. Rules will apply ${blockInfo}.`
    );

    setShowAddPartnerDialog(false);
  };

  const selectedPartnerData = mockPartners.find((p) => p.id === selectedPartner);
  const selectedPartnerRules = selectedPartner
    ? mockRules[selectedPartner] || []
    : [];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold text-zinc-50">
          Partner Management & Eligibility
        </h2>
        <p className="text-sm text-zinc-400">
          Configure rakeback partners and define eligibility rules without code
          changes
        </p>
      </div>

      {/* Add Partner Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleAddPartner}
          className="bg-zinc-800 hover:bg-zinc-700 text-zinc-100"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Partner
        </Button>
      </div>

      {/* Partner Registry */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h3 className="font-medium text-zinc-50">Partner Registry</h3>
          <p className="text-sm text-zinc-400 mt-1">
            All configured rakeback partners and their settings
          </p>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-zinc-900/50">
              <TableHead className="text-zinc-400">Partner Name</TableHead>
              <TableHead className="text-zinc-400">Type</TableHead>
              <TableHead className="text-zinc-400">Wallet / Tag</TableHead>
              <TableHead className="text-zinc-400 text-right">
                Rakeback Rate
              </TableHead>
              <TableHead className="text-zinc-400 text-right">
                Priority
              </TableHead>
              <TableHead className="text-zinc-400">Apply From</TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
              <TableHead className="text-zinc-400">Created By</TableHead>
              <TableHead className="text-zinc-400">Created Date</TableHead>
              <TableHead className="text-zinc-400"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {partners.map((partner) => (
              <TableRow
                key={partner.id}
                className="border-zinc-800 hover:bg-zinc-800/50 transition-colors"
              >
                <TableCell className="font-medium text-zinc-100">
                  {partner.name}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                    {partner.type}
                  </span>
                </TableCell>
                <TableCell className="font-mono text-zinc-300 text-sm max-w-xs truncate">
                  {partner.type === "Named" && partner.walletAddress && (
                    <span title={partner.walletAddress}>
                      {partner.walletAddress.slice(0, 12)}...{partner.walletAddress.slice(-8)}
                    </span>
                  )}
                  {partner.type === "Tag-based" && partner.memoTag && (
                    <span className="text-amber-400">"{partner.memoTag}"</span>
                  )}
                  {partner.type === "Hybrid" && (
                    <span className="text-zinc-400 text-xs">Multiple rules</span>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono text-zinc-100">
                  {partner.rakebackRate}%
                </TableCell>
                <TableCell className="text-right text-zinc-400">
                  {partner.priority}
                </TableCell>
                <TableCell className="text-zinc-400 text-sm">
                  {partner.applyFromDate || "Next block"}
                </TableCell>
                <TableCell>
                  <StatusBadge status={partner.status} />
                </TableCell>
                <TableCell className="text-zinc-400 text-sm">
                  {partner.createdBy}
                </TableCell>
                <TableCell className="text-zinc-400 text-sm">
                  {partner.createdDate}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEditRules(partner.id)}
                    className="text-zinc-400 hover:text-zinc-200"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Conflict Resolution Preview */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
        <div className="flex items-start gap-3 mb-4">
          <Shield className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-zinc-50">
              Conflict Resolution Rules
            </h3>
            <p className="text-sm text-zinc-400 mt-1">
              How the system handles wallets matching multiple partner rules
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4">
            <div className="text-sm text-zinc-300 mb-3">
              <span className="font-medium">Priority-Based Resolution:</span>{" "}
              When a wallet matches multiple partners, the partner with the
              lowest priority number wins.
            </div>
            <div className="space-y-2 text-sm">
              {partners
                .sort((a, b) => a.priority - b.priority)
                .map((partner) => (
                  <div key={partner.id} className="flex items-center gap-3 font-mono">
                    <span className="text-zinc-500 w-20">Priority {partner.priority}:</span>
                    <span className="text-zinc-100">
                      {partner.name} ({partner.rakebackRate}%)
                    </span>
                  </div>
                ))}
              {partners.length === 0 && (
                <div className="text-zinc-500 text-sm">
                  No partners configured yet
                </div>
              )}
            </div>
          </div>

          {partners.length >= 2 && (
            <div className="bg-amber-950/20 border border-amber-900/50 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-zinc-300">
                  <span className="font-medium text-amber-400">
                    Example Conflict:
                  </span>{" "}
                  If {partners.sort((a, b) => a.priority - b.priority)[0]?.name} custody wallet uses{" "}
                  {partners.sort((a, b) => a.priority - b.priority)[1]?.name} UI (memo contains
                  "{partners.sort((a, b) => a.priority - b.priority)[1]?.memoTag || "tag"}"), {partners.sort((a, b) => a.priority - b.priority)[0]?.name} wins due to higher priority.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Audit & Safety Guarantees */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6">
        <div className="flex items-start gap-3 mb-4">
          <CheckCircle className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-zinc-50">
              Audit & Safety Guarantees
            </h3>
            <p className="text-sm text-zinc-400 mt-1">
              How rule changes are applied and tracked
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4">
            <div className="text-emerald-400 mb-2 text-sm font-medium">
              ✓ Forward-Only Application
            </div>
            <div className="text-zinc-400 text-sm">
              Rule changes only affect future blocks. Past attributions remain
              immutable.
            </div>
          </div>

          <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4">
            <div className="text-emerald-400 mb-2 text-sm font-medium">
              ✓ Block-Height Tracking
            </div>
            <div className="text-zinc-400 text-sm">
              Every rule specifies the exact block height where it takes effect.
            </div>
          </div>

          <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4">
            <div className="text-emerald-400 mb-2 text-sm font-medium">
              ✓ Complete Audit Trail
            </div>
            <div className="text-zinc-400 text-sm">
              All changes logged with user, timestamp, before/after state.
            </div>
          </div>

          <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-lg p-4">
            <div className="text-emerald-400 mb-2 text-sm font-medium">
              ✓ Chain-Reproducible
            </div>
            <div className="text-zinc-400 text-sm">
              All attributions remain verifiable from on-chain data + rule
              history.
            </div>
          </div>
        </div>
      </div>

      {/* Rule Change Log */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-3">
          <History className="h-5 w-5 text-zinc-400" />
          <div>
            <h3 className="font-medium text-zinc-50">Rule Change Log</h3>
            <p className="text-sm text-zinc-400 mt-1">
              Immutable history of all partner configuration changes
            </p>
          </div>
        </div>
        <div className="divide-y divide-zinc-800">
          {ruleChangeLog.map((log, idx) => (
            <div
              key={idx}
              className="p-4 hover:bg-zinc-800/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-sm font-medium text-zinc-100">
                      {log.action}
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                      {log.partner}
                    </span>
                  </div>
                  <div className="text-sm text-zinc-400">{log.details}</div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
                    <span>By: {log.user}</span>
                    <span>•</span>
                    <span>Applies from block: {log.appliesFromBlock.toLocaleString()}</span>
                  </div>
                </div>
                <div className="text-xs text-zinc-500">{log.timestamp}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Edit Rules Dialog */}
      <Dialog open={showRulesDialog} onOpenChange={setShowRulesDialog}>
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-zinc-50">
              Eligibility Rules: {selectedPartnerData?.name}
            </DialogTitle>
            <DialogDescription className="text-zinc-400">
              Configure how wallets are attributed to this partner
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="rules" className="w-full">
            <TabsList className="bg-zinc-950 border border-zinc-800">
              <TabsTrigger value="rules">Active Rules</TabsTrigger>
              <TabsTrigger value="add-rule">Add New Rule</TabsTrigger>
            </TabsList>

            <TabsContent value="rules" className="space-y-4 mt-4">
              {selectedPartnerRules.length > 0 ? (
                <div className="space-y-3">
                  {selectedPartnerRules.map((rule) => (
                    <div
                      key={rule.id}
                      className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-4"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                            {rule.type === "wallet"
                              ? "Exact Wallet"
                              : rule.type === "memo"
                              ? "Memo Match"
                              : "Subnet Filter"}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-500">
                          From block {rule.appliesFromBlock.toLocaleString()}
                        </div>
                      </div>

                      {rule.type === "wallet" && (
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-zinc-500">Wallet:</span>
                            <div className="font-mono text-zinc-300 mt-1">
                              {rule.config.wallet}
                            </div>
                          </div>
                          {rule.config.label && (
                            <div>
                              <span className="text-zinc-500">Label:</span>
                              <div className="text-zinc-300 mt-1">
                                {rule.config.label}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {rule.type === "memo" && (
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-zinc-500">Memo String:</span>
                            <div className="font-mono text-zinc-300 mt-1">
                              "{rule.config.memoString}"
                            </div>
                          </div>
                          <div>
                            <span className="text-zinc-500">Match Type:</span>
                            <div className="text-zinc-300 mt-1">
                              {rule.config.matchType}
                            </div>
                          </div>
                          <div>
                            <span className="text-zinc-500">
                              Extrinsic Types:
                            </span>
                            <div className="flex gap-2 mt-1">
                              {rule.config.extrinsicTypes.map((type: string) => (
                                <span
                                  key={type}
                                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700"
                                >
                                  {type}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}

                      <div className="mt-3 pt-3 border-t border-zinc-800 text-xs text-zinc-500">
                        Created by {rule.createdBy} on {rule.createdAt}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-zinc-500">
                  <Info className="h-12 w-12 mx-auto mb-3" />
                  <div>No eligibility rules configured</div>
                  <div className="text-sm mt-1">
                    Add a rule to start attributing wallets
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="add-rule" className="space-y-4 mt-4">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="rule-type" className="text-zinc-300">
                    Rule Type
                  </Label>
                  <Select value={newRuleType} onValueChange={setNewRuleType}>
                    <SelectTrigger
                      id="rule-type"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-900 border-zinc-700">
                      <SelectItem value="wallet">Exact Wallet Address</SelectItem>
                      <SelectItem value="memo">Extrinsic Memo Match</SelectItem>
                      <SelectItem value="subnet">
                        Subnet Filter (Advanced)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {newRuleType === "wallet" && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="wallet-address" className="text-zinc-300">
                        Wallet Address
                      </Label>
                      <Input
                        id="wallet-address"
                        placeholder="5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="wallet-label" className="text-zinc-300">
                        Label (Optional)
                      </Label>
                      <Input
                        id="wallet-label"
                        placeholder="e.g., Creative Builds custody wallet"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      />
                    </div>
                    <div className="bg-blue-950/20 border border-blue-900/50 rounded-lg p-3 text-sm text-zinc-300">
                      <div className="flex items-start gap-2">
                        <Info className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                        <div>
                          Any stake or yield from this exact wallet address will
                          be attributed to {selectedPartnerData?.name}.
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {newRuleType === "memo" && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="memo-string" className="text-zinc-300">
                        Memo String
                      </Label>
                      <Input
                        id="memo-string"
                        placeholder="e.g., talisman"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="match-type" className="text-zinc-300">
                        Match Type
                      </Label>
                      <Select defaultValue="contains">
                        <SelectTrigger
                          id="match-type"
                          className="bg-zinc-950 border-zinc-800 text-zinc-100"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-700">
                          <SelectItem value="exact">Exact Match</SelectItem>
                          <SelectItem value="contains">Contains</SelectItem>
                          <SelectItem value="regex">Regex Pattern</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-zinc-300">
                        Applicable Extrinsic Types
                      </Label>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Switch id="extrinsic-stake" defaultChecked />
                          <Label
                            htmlFor="extrinsic-stake"
                            className="text-zinc-400"
                          >
                            Stake
                          </Label>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch id="extrinsic-unstake" defaultChecked />
                          <Label
                            htmlFor="extrinsic-unstake"
                            className="text-zinc-400"
                          >
                            Unstake
                          </Label>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch id="extrinsic-redelegate" defaultChecked />
                          <Label
                            htmlFor="extrinsic-redelegate"
                            className="text-zinc-400"
                          >
                            Redelegate
                          </Label>
                        </div>
                      </div>
                    </div>
                    <div className="bg-blue-950/20 border border-blue-900/50 rounded-lg p-3 text-sm text-zinc-300">
                      <div className="flex items-start gap-2">
                        <Info className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                        <div>
                          Wallets submitting matching extrinsics will be
                          automatically added to {selectedPartnerData?.name}'s
                          wallet registry.
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {newRuleType === "subnet" && (
                  <div className="space-y-4">
                    <div className="bg-amber-950/20 border border-amber-900/50 rounded-lg p-3 text-sm text-amber-300 mb-4">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                        <div>
                          <div className="font-medium mb-1">
                            Advanced Configuration
                          </div>
                          <div className="text-zinc-400">
                            Subnet filters are optional constraints applied on
                            top of wallet/memo rules.
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-zinc-300">Subnet Restrictions</Label>
                      <Textarea
                        placeholder="e.g., SN1, SN21, ROOT (comma-separated)"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-zinc-300">Stake Type Filter</Label>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Switch id="stake-tao" defaultChecked />
                          <Label htmlFor="stake-tao" className="text-zinc-400">
                            TAO Stake
                          </Label>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch id="stake-dtao" defaultChecked />
                          <Label htmlFor="stake-dtao" className="text-zinc-400">
                            dTAO Stake
                          </Label>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="space-y-2 pt-4 border-t border-zinc-800">
                  <Label className="text-zinc-300">
                    Rule Application Start
                  </Label>
                  <p className="text-xs text-zinc-500 mb-3">
                    Specify when this rule should take effect. Leave both empty to apply from the next block.
                  </p>
                  
                  {/* Date Option */}
                  <div className="space-y-2">
                    <Label htmlFor="rule-date" className="text-zinc-300 text-sm">
                      Apply From Date
                    </Label>
                    <Input
                      id="rule-date"
                      type="date"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:opacity-50"
                    />
                  </div>

                  {/* OR Separator */}
                  <div className="flex items-center gap-3 py-2">
                    <div className="h-px flex-1 bg-zinc-700"></div>
                    <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                      Or
                    </span>
                    <div className="h-px flex-1 bg-zinc-700"></div>
                  </div>

                  {/* Block Number Option */}
                  <div className="space-y-2">
                    <Label htmlFor="rule-block" className="text-zinc-300 text-sm">
                      Apply From Block
                    </Label>
                    <Input
                      id="rule-block"
                      type="number"
                      placeholder="e.g., 4521900"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono"
                    />
                  </div>
                  
                  <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-500 mt-3">
                    <div className="flex items-start gap-2">
                      <Info className="h-3.5 w-3.5 text-zinc-400 flex-shrink-0 mt-0.5" />
                      <div>
                        Choose one method: specify a date (system converts to block height) or enter an exact block number. Past blocks will not be affected.
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setShowRulesDialog(false)}
                    className="bg-zinc-950 border-zinc-800 text-zinc-300 hover:bg-zinc-900"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => {
                      toast.success("Rule added successfully");
                      setShowRulesDialog(false);
                    }}
                    className="bg-emerald-900 hover:bg-emerald-800 text-zinc-100"
                  >
                    Add Rule
                  </Button>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Add Partner Dialog */}
      <Dialog open={showAddPartnerDialog} onOpenChange={setShowAddPartnerDialog}>
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-zinc-50">Add New Partner</DialogTitle>
            <DialogDescription className="text-zinc-400">
              Configure partner details and eligibility rules
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Partner Basic Info */}
            <div className="space-y-4 pb-4 border-b border-zinc-800">
              <h4 className="text-sm font-medium text-zinc-300">
                Partner Information
              </h4>
              
              <div className="space-y-2">
                <Label htmlFor="partner-name" className="text-zinc-300">
                  Partner Name
                </Label>
                <Input
                  id="partner-name"
                  placeholder="e.g., Kraken"
                  className="bg-zinc-950 border-zinc-800 text-zinc-100"
                  value={partnerName}
                  onChange={(e) => setPartnerName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="partner-type" className="text-zinc-300">
                  Partner Type
                </Label>
                <Select
                  value={newPartnerType}
                  onValueChange={setNewPartnerType}
                  defaultValue="named"
                >
                  <SelectTrigger
                    id="partner-type"
                    className="bg-zinc-950 border-zinc-800 text-zinc-100"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-700">
                    <SelectItem value="named">Named (exact wallets)</SelectItem>
                    <SelectItem value="tag-based">
                      Tag-based (memo matching)
                    </SelectItem>
                    <SelectItem value="hybrid">
                      Hybrid (wallets + memos)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="rakeback-rate" className="text-zinc-300">
                    Rakeback Rate (%)
                  </Label>
                  <Input
                    id="rakeback-rate"
                    type="number"
                    placeholder="e.g., 15"
                    min="0"
                    max="100"
                    step="0.1"
                    className="bg-zinc-950 border-zinc-800 text-zinc-100"
                    value={rakebackRate}
                    onChange={(e) => setRakebackRate(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="priority" className="text-zinc-300">
                    Priority
                  </Label>
                  <Input
                    id="priority"
                    type="number"
                    placeholder="e.g., 3"
                    min="1"
                    className="bg-zinc-950 border-zinc-800 text-zinc-100"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  />
                  <p className="text-xs text-zinc-500">
                    Lower = higher priority
                  </p>
                </div>
              </div>
            </div>

            {/* Eligibility Rules */}
            <div className="space-y-4">
              <h4 className="text-sm font-medium text-zinc-300">
                Eligibility Rule Configuration
              </h4>

              {/* Named Partner - Wallet Address */}
              {newPartnerType === "named" && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="wallet-address" className="text-zinc-300">
                      Wallet Address
                    </Label>
                    <Input
                      id="wallet-address"
                      placeholder="5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono text-sm"
                      value={walletAddress}
                      onChange={(e) => setWalletAddress(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="wallet-label" className="text-zinc-300">
                      Wallet Label (Optional)
                    </Label>
                    <Input
                      id="wallet-label"
                      placeholder="e.g., Exchange custody wallet"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      value={walletLabel}
                      onChange={(e) => setWalletLabel(e.target.value)}
                    />
                  </div>
                  <div className="bg-blue-950/20 border border-blue-900/50 rounded-lg p-3 text-sm text-zinc-300">
                    <div className="flex items-start gap-2">
                      <Info className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                      <div>
                        Any stake or yield from this exact wallet address will be
                        attributed to this partner. You can add more wallets later.
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tag-based Partner - Memo/Keyword */}
              {newPartnerType === "tag-based" && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="memo-keyword" className="text-zinc-300">
                      Memo String / Keyword
                    </Label>
                    <Input
                      id="memo-keyword"
                      placeholder="e.g., kraken, binance, referral-123"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono"
                      value={memoKeyword}
                      onChange={(e) => setMemoKeyword(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="match-type" className="text-zinc-300">
                      Match Type
                    </Label>
                    <Select
                      defaultValue="contains"
                      value={matchType}
                      onValueChange={setMatchType}
                    >
                      <SelectTrigger
                        id="match-type"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      >
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-zinc-900 border-zinc-700">
                        <SelectItem value="exact">Exact Match</SelectItem>
                        <SelectItem value="contains">Contains</SelectItem>
                        <SelectItem value="regex">Regex Pattern</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-zinc-300">
                      Applicable Extrinsic Types
                    </Label>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <Switch id="tag-stake" defaultChecked />
                        <Label
                          htmlFor="tag-stake"
                          className="text-zinc-400"
                        >
                          Stake
                        </Label>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch id="tag-unstake" defaultChecked />
                        <Label
                          htmlFor="tag-unstake"
                          className="text-zinc-400"
                        >
                          Unstake
                        </Label>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch id="tag-redelegate" defaultChecked />
                        <Label
                          htmlFor="tag-redelegate"
                          className="text-zinc-400"
                        >
                          Redelegate
                        </Label>
                      </div>
                    </div>
                  </div>
                  <div className="bg-blue-950/20 border border-blue-900/50 rounded-lg p-3 text-sm text-zinc-300">
                    <div className="flex items-start gap-2">
                      <Info className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                      <div>
                        Wallets submitting extrinsics with this memo string will
                        be automatically attributed to this partner from on-chain data.
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Hybrid Partner - Both Wallet and Memo */}
              {newPartnerType === "hybrid" && (
                <div className="space-y-4">
                  <div className="space-y-4 pb-4 border-b border-zinc-800">
                    <div className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                      Wallet Address Rule
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="hybrid-wallet" className="text-zinc-300">
                        Wallet Address
                      </Label>
                      <Input
                        id="hybrid-wallet"
                        placeholder="5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono text-sm"
                        value={hybridWallet}
                        onChange={(e) => setHybridWallet(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="hybrid-wallet-label" className="text-zinc-300">
                        Wallet Label (Optional)
                      </Label>
                      <Input
                        id="hybrid-wallet-label"
                        placeholder="e.g., Primary custody wallet"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100"
                        value={hybridWalletLabel}
                        onChange={(e) => setHybridWalletLabel(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                      Memo Matching Rule
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="hybrid-memo" className="text-zinc-300">
                        Memo String / Keyword
                      </Label>
                      <Input
                        id="hybrid-memo"
                        placeholder="e.g., partner-referral"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono"
                        value={hybridMemo}
                        onChange={(e) => setHybridMemo(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="hybrid-match" className="text-zinc-300">
                        Match Type
                      </Label>
                      <Select
                        defaultValue="contains"
                        value={hybridMatchType}
                        onValueChange={setHybridMatchType}
                      >
                        <SelectTrigger
                          id="hybrid-match"
                          className="bg-zinc-950 border-zinc-800 text-zinc-100"
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-700">
                          <SelectItem value="exact">Exact Match</SelectItem>
                          <SelectItem value="contains">Contains</SelectItem>
                          <SelectItem value="regex">Regex Pattern</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="bg-blue-950/20 border border-blue-900/50 rounded-lg p-3 text-sm text-zinc-300">
                    <div className="flex items-start gap-2">
                      <Info className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                      <div>
                        Hybrid partners combine exact wallet matching with memo-based
                        attribution for maximum flexibility.
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Applies From Block */}
              <div className="space-y-2 pt-4 border-t border-zinc-800">
                <Label className="text-zinc-300">
                  Rule Application Start
                </Label>
                <p className="text-xs text-zinc-500 mb-3">
                  Specify when this rule should take effect. Leave both empty to apply from the next block.
                </p>
                
                {/* Date Option */}
                <div className="space-y-2">
                  <Label htmlFor="rule-date" className="text-zinc-300 text-sm">
                    Apply From Date
                  </Label>
                  <Input
                    id="rule-date"
                    type="date"
                    className="bg-zinc-950 border-zinc-800 text-zinc-100 [&::-webkit-calendar-picker-indicator]:invert [&::-webkit-calendar-picker-indicator]:opacity-50"
                    value={applyFromDate}
                    onChange={(e) => setApplyFromDate(e.target.value)}
                  />
                </div>

                {/* OR Separator */}
                <div className="flex items-center gap-3 py-2">
                  <div className="h-px flex-1 bg-zinc-700"></div>
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Or
                  </span>
                  <div className="h-px flex-1 bg-zinc-700"></div>
                </div>

                {/* Block Number Option */}
                <div className="space-y-2">
                  <Label htmlFor="rule-block" className="text-zinc-300 text-sm">
                    Apply From Block
                  </Label>
                  <Input
                    id="rule-block"
                    type="number"
                    placeholder="e.g., 4521900"
                    className="bg-zinc-950 border-zinc-800 text-zinc-100 font-mono"
                    value={applyFromBlock}
                    onChange={(e) => setApplyFromBlock(e.target.value)}
                  />
                </div>
                
                <div className="bg-zinc-950/50 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-500 mt-3">
                  <div className="flex items-start gap-2">
                    <Info className="h-3.5 w-3.5 text-zinc-400 flex-shrink-0 mt-0.5" />
                    <div>
                      Choose one method: specify a date (system converts to block height) or enter an exact block number. Past blocks will not be affected.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-zinc-800">
              <Button
                variant="outline"
                onClick={() => setShowAddPartnerDialog(false)}
                className="bg-zinc-950 border-zinc-800 text-zinc-300 hover:bg-zinc-900"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSavePartner}
                className="bg-emerald-900 hover:bg-emerald-800 text-zinc-100"
              >
                Create Partner & Rule
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}