## Ethernet Network Setup

To enable Ethernet connectivity on the DE10 via an Ethernet-to-USB-C dongle, follow these steps:

1. **Enable Internet Sharing on your MacBook:**
   - On your Mac:
     - Open **System Preferences**.
     - Go to **Sharing**.
     - Select **Internet Sharing** from the list.
     - Choose your primary network interface (e.g., Wi-Fi) as the source.
     - Share your connection to the Ethernet adapter (the USB-C dongle).
     - Turn on Internet Sharing. This will allow the DE10 to access the Internet via your MacBook.
   
2. **Configure the Ethernet on the DE10:**
   - Once the Ethernet-to-USB-C dongle is connected to the DE10, perform the following:
     - **Check the Ethernet interface:**
       ```bash
       ifconfig eth0
       ```
     - **Initialize network configuration via DHCP:**
       ```bash
       sudo dhclient eth0
       ```
     - **Test the network connection:**
       ```bash
       timeout 5s ping google.com
       ```
     - If the ping is successful, your DE10 now has Internet connectivity.

   **Note:** If `eth0` is not present or named differently, use `ip a` to identify the correct network interface.
   
3. **Set Up Remote Access via SSH:**
   - To enable remote access, install the OpenSSH server on the DE10-Nano by running:
     ```bash
     sudo apt-get install openssh-server
     ```
   - This allows you to connect to the DE10 via SSH for debugging or remote management.