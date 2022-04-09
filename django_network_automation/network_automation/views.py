from multiprocessing import context
from pyexpat.errors import messages
import re
from sys import stdin, stdout
from unittest import result
from django.shortcuts import get_object_or_404, render, HttpResponse, get_list_or_404, redirect
from .models import Device, Log
import paramiko,time
from datetime import datetime

def home(request):
    all_device = Device.objects.all()
    cisco_device = Device.objects.filter(vendor = "cisco")
    mikrotik_device = Device.objects.filter(vendor = "mikrotik")
    last_event = Log.objects.all().order_by('-id')[:10]

    context = {
        'all_device': len(all_device),
        'cisco_device' : len(cisco_device),
        'mikrotik_device' : len(mikrotik_device),
        'last_event': last_event
    }
    
    return render(request, 'home.html', context)

def devices(request):
    all_device = Device.objects.all()

    context = {
        'all_device' : all_device
    }

    return render(request, 'devices.html', context)

def configure(request):
    if request.method == "POST":
        print("tests")
        selected_device_id = request.POST.getlist('device')
        mikrotik_command = request.POST['mikrotik_command'].splitlines()
        cisco_command = request.POST['cisco_command'].splitlines()
        for x in selected_device_id:
            try:
                dev = get_object_or_404(Device, pk = x)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=dev.ip_address,username=dev.username,password=dev.password)

                if dev.vendor.lower() == 'cisco':
                    conn = ssh_client.invoke_shell()
                    conn.send("conf t\n")
                    for cmd in cisco_command:
                        conn.send(cmd + "\n")
                        time.sleep(1)
                else:
                    for cmd in mikrotik_command:
                        ssh_client.exec_command(cmd)
                log = Log(target=dev.ip_address, action="configure", status="success", time=datetime.now(), messages="No Error")
                log.save()
            except Exception as e:
                log = Log(target=dev.ip_address, action="configure", status="error", time=datetime.now(), messages=e)
                log.save()
        return redirect('home')

    else:
            devices = Device.objects.all()
            context = {
                'devices': devices,
                'mode': 'configure'

            }
            return render(request, 'config.html', context)


def verify_config(request):
    if request.method == "POST":
        result = []
        selected_device_id = request.POST.getlist('device')
        mikrotik_command = request.POST['mikrotik_command'].splitlines()
        cisco_command = request.POST['cisco_command'].splitlines()
        for x in selected_device_id:
            try:
                dev = get_object_or_404(Device, pk=x)
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_client.connect(hostname=dev.ip_address,username=dev.username,password=dev.password)

                if dev.vendor.lower() == 'mikrotik':
                    for cmd in mikrotik_command:
                        stdin,stdout,stderr = ssh_client.exec_command(cmd)
                        result.append("Result on {}".format(dev.ip_address))
                        result.append(stdout.read().decode())
                else:
                    conn = ssh_client.invoke_shell()
                    conn.send('terminal length 0\n')
                    for cmd in cisco_command:
                        result.append("Result on {}".format(dev.ip_address))
                        conn.send(cmd + "\n")
                        time.sleep(1)
                        output = conn.recv(65535)
                        result.append(output.decode())
                log = Log(target=dev.ip_address, action="verify config", status="success", time=datetime.now(), messages="No Error")
                log.save()
            except Exception as e:
                    log = Log(target=dev.ip_address, action="verify config", status="error", time=datetime.now(), messages=e)
                    log.save()
        result = '\n'.join(result)
        return render(request, 'verify_result.html', {'result':result})
    else:
        devices = Device.objects.all()
        context = {
            'devices': devices,
            'mode': 'verify config'
        }
        return render(request, 'config.html', context)


def log(request):
    logs = Log.objects.all()

    context = {
        'logs': logs
    }

    return render(request, 'log.html', context)
