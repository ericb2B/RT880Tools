Tools for nicfw for rt-880 and uv-98

For use connect the programmation câble to Rt-880, Rt-880g or Uv98 to the computer.

Modify the configuration file according you need. Run the script.

what the script do :

Read the lastest beacon from the radio. Compare géographic position read and the previous read.

If the position not match, the sms is send.or/and send to an mqtt server

It's usefull for that ?

For exemple in case of emergency. A user in difficulty send beacon, to the base station (RT-880 + Computer), the sms is send directly to an emergency personne.

Why sms and not internet ?

Because sms, work in most case and not need special software. Sms need a ridiculous connection, and is send or receive, when a gsm connexion is possible, with no human manipulation.
