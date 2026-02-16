import { createBrowserRouter } from "react-router";
import { Layout } from "./components/layout";
import SystemOverview from "./pages/system-overview";
import BlockAttribution from "./pages/block-attribution";
import BlockDetail from "./pages/block-detail";
import ConversionEvents from "./pages/conversion-events";
import PartnerLedger from "./pages/partner-ledger";
import DataCompleteness from "./pages/data-completeness";
import PartnerManagement from "./pages/partner-management";
import ApiSettings from "./pages/api-settings";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: SystemOverview },
      { path: "block-attribution", Component: BlockAttribution },
      { path: "block-detail/:blockNumber", Component: BlockDetail },
      { path: "conversion-events", Component: ConversionEvents },
      { path: "partner-ledger", Component: PartnerLedger },
      { path: "data-completeness", Component: DataCompleteness },
      { path: "partner-management", Component: PartnerManagement },
      { path: "api-settings", Component: ApiSettings },
    ],
  },
]);