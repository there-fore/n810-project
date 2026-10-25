#!/bin/sh
# Switch the N810 to USB networking one step at a time (run as root).
# Usage: sh usbnet.sh 1|2|3|4|otg|status|stop
#   1 stop ke-recv   2 unload drive mode   3 load g_ether   4 bring up usb0
#   status = show state   stop = undo everything (back to USB drive mode)
MOD=/mnt/initfs/lib/modules/`uname -r`
status() {
    echo "-- ke-recv running: `ps | grep -c '[k]e-recv'`"
    echo "-- USB drivers:"; lsmod | grep '^g_' || echo "   (none)"
    echo "-- USB mode: `cat /sys/devices/platform/musb_hdrc/mode`"
    echo "-- usb0:"; /sbin/ifconfig usb0 2>/dev/null | grep -E 'inet addr|UP' || echo "   (not up)"
    echo "-- wlan0: `/sbin/ifconfig wlan0 | grep 'inet addr' | sed 's/^ *//'`"
    echo "-- last USB kernel messages:"
    dmesg | grep -i -E 'gadget|ether|rndis|usb0|musb|g_file' | tail -5
}
case "$1" in
1) echo "## 1. stop the USB-drive daemon"; /etc/init.d/ke-recv stop ;;
2) echo "## 2. unload USB-drive mode"; rmmod g_file_storage ;;
3) echo "## 3. load the network driver"; insmod $MOD/g_ether.ko ;;
4) echo "## 4. give the cable an address"; /sbin/ifup usb0 ;;
otg) echo "## set the USB port to OTG (as nm-usb-setup start does)"; echo otg > /sys/devices/platform/musb_hdrc/mode ;;
stop) echo "## undo: back to USB-drive mode"; /usr/sbin/nm-usb-setup stop ;;
status) ;;
*) echo "usage: sh usbnet.sh 1|2|3|4|status|stop"; exit 1 ;;
esac
echo "exit code: $?"
sleep 1
status
