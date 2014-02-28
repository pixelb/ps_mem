ps_mem
======

A utility to accurately report the core memory usage for a program

Yes the name is a bit weird. coremem would be more appropriate,
but for backwards compatible reasons the ps_mem name remains.

Usage:

```
ps_mem [-h|--help] [-s|--split-args] [-p PID] [-P|--processes PROCNAME] [-w N]
```

Example output:

```
 Private  +   Shared  =  RAM used       Program

 34.6 MiB +   1.0 MiB =  35.7 MiB       gnome-terminal
139.8 MiB +   2.3 MiB = 142.1 MiB       firefox
291.8 MiB +   2.5 MiB = 294.3 MiB       gnome-shell
272.2 MiB +  43.9 MiB = 316.1 MiB       chrome (12)
913.9 MiB +   3.2 MiB = 917.1 MiB       thunderbird
---------------------------------
                          1.9 GiB
=================================
```

The [-p PID] option allows filtering the results.
For example to restrict output to the current $USER you could:

```
sudo ps_mem -p $(pgrep -u $USER | paste -d, -s)
```

The [-P|--processes PROCNAME] option allows filtering the results.
For example to restrict output the process chrome you could:

```
sudo ps_mem -P chrome
 Private  +   Shared  =  RAM used	Program

272.2 MiB +  43.9 MiB = 316.1 MiB       chrome (12)
---------------------------------
                        316.1 MiB
=================================

```
