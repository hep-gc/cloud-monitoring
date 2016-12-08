#!/bin/bash
echo
date

# ======================================================================================
# declare and initialize variables
# ======================================================================================
vmFile="/var/log/vm_defunct.log"
retireFile="/tmp/retireCommand.txt"
destroyFile="/tmp/destroyCommand.txt"
retireCommands=""
destroyCommands=""
retireFlag=0
destroyFlag=0

# extract VM name and number of Slots
# ===================================
defunctVmList=`cat $vmFile | awk '{OFS=",";print $22}' | sed 's/"//g' | sed 's/,//g' `
defunctSlotList=`cat $vmFile | awk '{OFS=",";print $4}' | sed 's/"//g' | sed 's/,//g' `

declare -a vm
i=0
for line in $defunctVmList; do
   vm[$i]=${line}
   let "i+=1"
done

declare -a slots
i=0
for line in $defunctSlotList; do
   slots[$i]=${line}
   let "i+=1"
done

# echo "vms = "
# echo ${vm[*]}

# echo "slots = "
# echo ${slots[*]}

# ======================================================================================
# Loop over each VM in the defunct list
# ======================================================================================
#
i=0
for line in ${vm[@]}
do
   # echo
   echo "VM : " ${line}

   # retrieve information about the VM
   # =================================
   vmInfo=`cloud_status -m | grep ${line} `
   # echo "vmInfo : " $vmInfo

   # Test if the VM is still running
   # ===============================
   if [[ $vmInfo == "" ]]; then
      echo "===> The VM does not exist  :" ${line}
      let "i+=1"
      continue
   fi
   vmID=` echo $vmInfo | awk '{print $1}' `
   vmStatus=` echo $vmInfo | awk '{print $5}' `
   cloudName=` echo $vmInfo | awk '{print $6}' `

   # get number of running jobs (dynamic slots)
   # =========================================
   if [[ $cloudName == "cc-west" ]]; then
      fullVmName=${line}".westcloud"
   elif [[ $cloudName == "cc-west-belle" ]]; then
      fullVmName=${line}".westcloud"
   elif [[ $cloudName == "cc-east" ]]; then
      fullVmName=${line}".openstacklocal"
   else
      fullVmName=${line}
   fi

   nJobs=`condor_status -format "%s\n" NumDynamicSlots $fullVmName`

   echo "vmID=" $vmID " cloudName=" $cloudName " slots=" ${slots[$i]} " status=" $vmStatus, " jobs=" $nJobs

   # retire the VM if the number of jobs and slots are not equal
   # ===========================================================
   if [[ ${slots[$i]} !=  $nJobs ]];  then
      if [[ $vmStatus != "Retiring" ]] ;  then
         echo "===> Retire the VM"
         a="cloud_admin -o -c "$cloudName" -n"$vmID
         # echo $a
         retireCommands="$retireCommands\n$a"
         retireFlag=1
      fi
      let "i+=1"
      continue
   fi

   # find the job associated to the VM
   # =================================
   jobNumber=`condor_q -run | grep ${line} |  awk '{print $1}' `
   if [[ jobNumber == "" ]]; then
      echo "===> JobNumber is null;  nothing to remove"
      let "i+=1"
      continue
   fi
   echo "===> Remove the job and destroy this VM"
   a="sudo condor_rm "${jobNumber}
   # echo $a
   destroyCommands="$destroyCommands\n$a"

   # destroy the VM
   # ==============
   a="cloud_admin -k -c "${cloudName}" -n "$vmID
   # echo $a
   destroyCommands="$destroyCommands\n$a"
   destroyFlag=1

   let "i+=1"
done


# remove old command files (add destroyFile later)
# ========================
if [[ -f $retireFile ]]; then
   echo "File exists:" $retireFile   "===> Remove it"
   rm $retireFile
fi 

# print commands to file
# ======================
if [[ $retireFlag == "1" ]]; then
   echo "Copy retire commands to file"
   echo -e ${retireCommands} > $retireFile
   echo "Running : " $retireFile
   cat $retireFile
   source $retireFile
fi

echo -e ${destroyCommands} > $destroyFile

