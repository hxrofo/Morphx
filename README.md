# Morphx
## The Art of Obfuscating Android Payloads  
![interface](https://github.com/user-attachments/assets/4883614e-6de0-41c7-8c64-d736bba8567e)

## What does this script do?  
### It has 5 options:  
**1)** Generates a simple MSF payload using MSFVENOM (no obfuscation)  

**2)** Takes an original app and injects MSF payload into it (METHOD 1/Obfuscated/Without "Msfvenom -x")  

**3)** Takes an original app and injects MSF payload into it (METHOD 2/Obfuscated/ Using "Msfvenom -x")  

**4)** Generates a payload and changes default strings and icon. (Obfuscated)  

**5)** Generates a payload like option 2 and injects a new MainActivity for persistence after reboot. (Persistent, Obfuscated)  

## How to use?  
git clone https://github.com/hxrofo/Morphx.git  

cd Morphx  

chmod +x morphx  

./morphx  

There are two subfolders next to the script, "input" is where you put your PNG icons, MainActivity.smali, the original apps to be backdoored and apktool.jar.  

When you first run the script, it will create another folder, "output" where you can find your compiled payload/apk.

