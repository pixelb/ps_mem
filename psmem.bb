#
# ps_mem
#
SUMMARY = "A utility to accurately report the in core memory usage for a program"
HOMEPAGE = "https://github.com/pixelb/ps_mem"
LICENSE = "LGPLv2"
LIC_FILES_CHKSUM = "file://LICENSE;md5=c05fdef0c0d05f619748e9bb0fb41b21"

PR = "r0"

SRC_URI = "git://github.com/pixelb/ps_mem.git;branch=master;protocol=git"
SRCREV = "702b461d16062f14a9f4191bc731adcf48b51489"

S = "${WORKDIR}/git"

do_compile () {
	echo "No compile needed"
}

do_install () {
	install -d ${D}${bindir}
	install -m 0755 ${S}/ps_mem.py ${D}${bindir}/ps_mem
}

FILES_${PN} += "/*"
FILES_${PN}-dbg += "/www/pages/.debug"
