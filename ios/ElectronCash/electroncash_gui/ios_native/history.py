from . import utils
from . import gui
from electroncash import WalletStorage, Wallet
from electroncash.util import timestamp_to_datetime
import time

try:
    from .uikit_bindings import *
except Exception as e:
    sys.exit("Error: Could not import iOS libs: %s"%str(e))

# History Tab -- shows tx's, etc
class HistoryTableVC(UITableViewController):
    needsRefresh = objc_property()
    statusImages = objc_property()

    @objc_method
    def initWithStyle_(self, style : int):
        self = ObjCInstance(send_super(self, 'initWithStyle:', style, argtypes=[c_int]))
        self.needsRefresh = False
        # setup the status icons array.. cache the images basically
        self.statusImages = NSMutableArray.arrayWithCapacity_(10)
        tx_icons = [
            "warning.png",
            "warning.png",
            "unconfirmed.png",
            "unconfirmed.png",
            "clock1.png",
            "clock2.png",
            "clock3.png",
            "clock4.png",
            "clock5.png",
            "confirmed.png",
        ]
        for icon in tx_icons:
            img = utils.uiimage_get(icon)
            if img is not None:
                self.statusImages.addObject_(img)        
        return self

    @objc_method
    def dealloc(self) -> None:
        self.needsRefresh = None
        self.statusImages = None
        send_super(self, 'dealloc')

    @objc_method
    def numberOfSectionsInTableView_(self, tableView) -> int:
        return 1

    @objc_method
    def tableView_numberOfRowsInSection_(self, tableView, section) -> int:
        try:
            parent = gui.ElectrumGui.gui
            return len(parent.history)
        except:
            print("Error, no history")
            return 0

    @objc_method
    def tableView_cellForRowAtIndexPath_(self, tableView, indexPath):
        cell = tableView.dequeueReusableCellWithIdentifier_("row")
        if cell is None:
            cell = UITableViewCell.alloc().initWithStyle_reuseIdentifier_(UITableViewCellStyleSubtitle, "row").autorelease()
        try:
            parent = gui.ElectrumGui.gui
            entry = parent.history[indexPath.row]
            t = ("%s | Amt: %s | Bal: %s"%(entry[2],entry[4],entry[5]))
            ff = entry[6]
            conf = entry[7]
            status = entry[8]
            if conf > 0:
                ff = "%s confirmations"%conf
            t2 = ("%s | %s"%(ff,entry[3]))
            if status >= 0 and status < len(self.statusImages):
                cell.imageView.image = self.statusImages[status]
            else:
                cell.imageView.image = None
            cell.textLabel.text = t
            cell.textLabel.adjustsFontSizeToFitWidth = True
            cell.detailTextLabel.text = t2
            #cell.detailTextLabel.lineBreakMode = NSLineBreakByWordWrapping
            cell.detailTextLabel.adjustsFontSizeToFitWidth = True
        except:
            cell.textLabel.text = "*Error*"
        return cell
    
    @objc_method
    def updateHistoryFromWallet(self):
        parent = gui.ElectrumGui.gui
        wallet = parent.wallet
        h = wallet.get_history()
        #item = self.currentItem()
        #current_tx = item.data(0, Qt.UserRole) if item else None
        #self.clear()
        #fx = parent.fx
        #if fx: fx.history_used_spot = False
        parent.history = []
        for h_item in h:
            tx_hash, height, conf, timestamp, value, balance = h_item
            status, status_str = wallet.get_tx_status(tx_hash, height, conf, timestamp)
            has_invoice = wallet.invoices.paid.get(tx_hash)
            #icon = QIcon(":icons/" + TX_ICONS[status])
            v_str = parent.format_amount(value, True, whitespaces=True)
            balance_str = parent.format_amount(balance, whitespaces=True)
            label = wallet.get_label(tx_hash)
            date = timestamp_to_datetime(time.time() if conf <= 0 else timestamp)
            entry = ['', tx_hash, status_str, label, v_str, balance_str, date, conf, status]
            parent.history.insert(0,entry) # reverse order
            #if fx and fx.show_history():
            #    date = timestamp_to_datetime(time.time() if conf <= 0 else timestamp)
            #    for amount in [value, balance]:
            #        text = fx.historical_value_str(amount, date)
            #        entry.append(text)
            #item = SortableTreeWidgetItem(entry)
            #item.setIcon(0, icon)
            #item.setToolTip(0, str(conf) + " confirmation" + ("s" if conf != 1 else ""))
            #item.setData(0, SortableTreeWidgetItem.DataRole, (status, conf))
            #if has_invoice:
            #    item.setIcon(3, QIcon(":icons/seal"))
            #for i in range(len(entry)):
            #    if i>3:
            #        item.setTextAlignment(i, Qt.AlignRight)
            #    if i!=2:
            #        item.setFont(i, QFont(MONOSPACE_FONT))
            #if value and value < 0:
            #    item.setForeground(3, QBrush(QColor("#BC1E1E")))
            #    item.setForeground(4, QBrush(QColor("#BC1E1E")))
            #if tx_hash:
            #    item.setData(0, Qt.UserRole, tx_hash)
            #self.insertTopLevelItem(0, item)
            #if current_tx == tx_hash:
            #    self.setCurrentItem(item)
        print ("fetched %d entries from history"%len(parent.history))


    @objc_method
    def refresh(self):
        self.updateHistoryFromWallet()
        try:
            self.refreshControl.endRefreshing()
        except:
            pass
        self.tableView.reloadData()
        self.needsRefresh = False

    @objc_method
    def needUpdate(self):
        self.needsRefresh = True

    # This method runs in the main thread as it's enqueue using our hacky "Heartbeat" mechanism/workaround for iOS
    @objc_method
    def doRefreshIfNeeded(self):
        if self.needsRefresh:
            self.refresh()

    @objc_method
    def showRefreshControl(self):
        if self.refreshControl is not None and not self.refreshControl.isRefreshing():
            # the below starts up the table view in the "refreshing" state..
            self.refreshControl.beginRefreshing()
            self.tableView.setContentOffset_animated_(CGPointMake(0, self.tableView.contentOffset.y-self.refreshControl.frame.size.height), True)
