# Morphx
## The Art of Obfuscating Android Payloads  
## ![1](https://github.com/user-attachments/assets/34749752-f481-4f66-a012-787b2e0ccdf5)

## What does this script do?  
### It has 4 options:  
**1)** Generates a simple MSF payload using MSFVENOM (no obfuscation)  
**2)** Takes an original app and injects MSF payload into it (Obfuscated)  
**3)** Generates a payload and changes default strings and icon. (Obfuscated)  
**4)** Generates a payload like option 3 and injects a new MainActivity for persistence after reboot. (Persistent, Obfuscated)  

## How to use?  
git clone https://github.com/hxrofo/Morphx.git  
cd Morphx  
chmod +x Morphx  
./morphx  

There are two subfolders next to the script, "input" is where you put your PNG icons, MainActivity.smali, the original apps to be backdoored and apktool.jar. When you first run the script, it will create another folder, "output" where you can find your compiled payload/apk.

