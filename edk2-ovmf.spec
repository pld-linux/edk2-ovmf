# NOTE: the firmware itself is compiled with edk2's own toolchain flags
# (BaseTools/Conf/tools_def.template, GCC tag); %%{rpmcflags} only reach
# the BaseTools host utilities.
%define		edk2ver		202608
# CryptoPkg/Library/OpensslLib/openssl submodule commit at edk2-stable%%{edk2ver} (OpenSSL 3.5.7)
%define		openssl_commit	8cf17aaeb4599f8af87fefd810b5b5fee90fe69e
# Microsoft DBX (revocation list) release, https://github.com/microsoft/secureboot_objects
%define		sbo_ver		1.7.0
Summary:	OVMF - UEFI firmware for x86_64 virtual machines
Summary(pl.UTF-8):	OVMF - firmware UEFI dla maszyn wirtualnych x86_64
Name:		edk2-ovmf
Version:	%{edk2ver}
Release:	1
License:	BSD+patent (firmware), Apache v2.0 (bundled OpenSSL)
Group:		Applications/System
Source0:	https://github.com/tianocore/edk2/archive/refs/tags/edk2-stable%{edk2ver}.tar.gz
# Source0-md5:	02735bb4c949f027310c26e541f52c78
Source1:	https://github.com/openssl/openssl/archive/%{openssl_commit}/openssl-8cf17aa.tar.gz
# Source1-md5:	ed255b58a1657618d6de5c57578b59cc
# qemu firmware descriptors (docs/interop/firmware.json), used by libvirt
Source2:	30-edk2-ovmf-x64-sb-enrolled.json
Source3:	40-edk2-ovmf-x64-sb.json
Source4:	50-edk2-ovmf-x64-nosb.json
# DBX updates signed by the Microsoft KEK 2011 and KEK 2023 CAs
Source5:	https://github.com/microsoft/secureboot_objects/releases/download/v%{sbo_ver}-signed/edk2-2011-signed-secureboot-binaries.tar.gz?/secureboot-objects-2011-signed-%{sbo_ver}.tar.gz
# Source5-md5:	be66a2576824d196ebc57f5c360f017d
Source6:	https://github.com/microsoft/secureboot_objects/releases/download/v%{sbo_ver}-signed/edk2-2023-signed-secureboot-binaries.tar.gz?/secureboot-objects-2023-signed-%{sbo_ver}.tar.gz
# Source6-md5:	085653c88c54877598a3a8b404bbb6fb
Patch0:		%{name}-basetools-no-brotli.patch
# from Fedora/Debian: makes PcdUninstallMemAttrProtocol (and the
# opt/org.tianocore/UninstallMemAttrProtocol fw_cfg key) work on OvmfPkgX64
Patch1:		%{name}-uninstall-memattr-protocol.patch
URL:		https://github.com/tianocore/tianocore.github.io/wiki/OVMF
BuildRequires:	acpica
BuildRequires:	gcc-c++
BuildRequires:	libuuid-devel
BuildRequires:	nasm
BuildRequires:	python3
BuildRequires:	python3-virt-firmware
ExclusiveArch:	%{x8664}
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%define		_enable_debug_packages	0

%define		ovmfdir		%{_datadir}/OVMF

%description
OVMF (Open Virtual Machine Firmware) is a port of the EDK II UEFI
firmware to QEMU/KVM virtual machines. This package contains the
x86_64 4 MB flash images: firmware code with and without Secure Boot
support, matching variable stores (including one with the Microsoft
UEFI certificates pre-enrolled), a unified image for use with a single
flash device, and QEMU firmware descriptors.

%description -l pl.UTF-8
OVMF (Open Virtual Machine Firmware) to port firmware'u UEFI EDK II do
maszyn wirtualnych QEMU/KVM. Ten pakiet zawiera 4-megabajtowe obrazy
flash dla x86_64: kod firmware'u z obsługą Secure Boot i bez niej,
pasujące magazyny zmiennych (w tym jeden ze wstępnie zarejestrowanymi
certyfikatami UEFI Microsoftu), obraz scalony do użycia z pojedynczym
urządzeniem flash oraz deskryptory firmware'u dla QEMU.

%prep
%setup -q -n edk2-edk2-stable%{edk2ver} -a1
%patch -P0 -p1
%patch -P1 -p1

rmdir CryptoPkg/Library/OpensslLib/openssl
mv openssl-%{openssl_commit} CryptoPkg/Library/OpensslLib/openssl

# OVMF and OpenSSL license files share the top-level file names
cp -p OvmfPkg/License.txt License.OvmfPkg.txt
cp -p CryptoPkg/Library/OpensslLib/openssl/LICENSE.txt LICENSE.openssl.txt

install -d dbx-2011 dbx-2023
tar xzf %{SOURCE5} -C dbx-2011
tar xzf %{SOURCE6} -C dbx-2023

# .dec files declare include paths inside submodules that OVMF never
# builds; the meta-data parser only checks that the directories exist
install -d MdePkg/Library/MipiSysTLib/mipisyst/library/include \
	MdeModulePkg/Library/BrotliCustomDecompressLib/brotli/c/include \
	CryptoPkg/Library/MbedTlsLib/mbedtls/include/mbedtls \
	CryptoPkg/Library/MbedTlsLib/mbedtls/library \
	SecurityPkg/DeviceSecurity/SpdmLib/libspdm/include

%build
export PYTHON_COMMAND=%{__python3}
%{__make} -C BaseTools \
	EXTRA_OPTFLAGS="%{rpmcflags}" \
	EXTRA_LDFLAGS="%{rpmldflags}"

export WORKSPACE=$(pwd)
export EDK_TOOLS_PATH=$WORKSPACE/BaseTools
. ./edksetup.sh BaseTools

# --pcd string values get their quotes from build.py (a bare L prefix).
# PcdUninstallMemAttrProtocol: older shim/grub crash under strict NX
# memory protection (same workaround as Debian and Fedora)
build_ovmf() {
	build -a X64 -t GCC -b RELEASE -p OvmfPkg/OvmfPkgX64.dsc \
		%{?__jobs:-n %{__jobs}} \
		-D FD_SIZE_4MB \
		-D TPM2_ENABLE=TRUE \
		-D NETWORK_HTTP_BOOT_ENABLE=TRUE \
		-D NETWORK_IP6_ENABLE=TRUE \
		-D NETWORK_TLS_ENABLE=TRUE \
		--pcd PcdUninstallMemAttrProtocol=TRUE \
		--pcd 'PcdFirmwareVendor=LPLD Linux distribution of EDK II\0' \
		--pcd 'PcdFirmwareVersionString=Ledk2-stable%{edk2ver}\0' \
		"$@"
}

build_ovmf
cp -p Build/OvmfX64/RELEASE_GCC/FV/OVMF_CODE.fd OVMF_CODE_4M.fd
cp -p Build/OvmfX64/RELEASE_GCC/FV/OVMF_VARS.fd OVMF_VARS_4M.fd
cp -p Build/OvmfX64/RELEASE_GCC/FV/OVMF.fd OVMF_4M.fd
rm -rf Build/OvmfX64

# the UEFI shell would let any guest bypass Secure Boot
build_ovmf -D SECURE_BOOT_ENABLE=TRUE -D SMM_REQUIRE=TRUE -D BUILD_SHELL=FALSE
cp -p Build/OvmfX64/RELEASE_GCC/FV/OVMF_CODE.fd OVMF_CODE_4M.secboot.fd

# throwaway build-time certificate as PK/KEK (a PK is needed to leave
# Setup Mode), Microsoft KEK and db certificates, Microsoft dbx revocations
virt-fw-vars \
	--input Build/OvmfX64/RELEASE_GCC/FV/OVMF_VARS.fd \
	--output OVMF_VARS_4M.ms.fd \
	--enroll-generate "PLD Linux" \
	--set-dbx dbx-2011/dbx_x64_Legacy/dbx_x64_Legacy.efiauth2 \
	--add-dbx dbx-2023/dbx_x64.efiauth2 \
	--secure-boot

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT{%{ovmfdir},%{_datadir}/qemu/firmware}

cp -p OVMF_4M.fd OVMF_CODE_4M.fd OVMF_VARS_4M.fd OVMF_CODE_4M.secboot.fd OVMF_VARS_4M.ms.fd \
	$RPM_BUILD_ROOT%{ovmfdir}
ln -sf OVMF_CODE_4M.secboot.fd $RPM_BUILD_ROOT%{ovmfdir}/OVMF_CODE_4M.ms.fd

cp -p %{SOURCE2} %{SOURCE3} %{SOURCE4} $RPM_BUILD_ROOT%{_datadir}/qemu/firmware

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%doc License.txt License-History.txt License.OvmfPkg.txt LICENSE.openssl.txt OvmfPkg/README
%dir %{ovmfdir}
%{ovmfdir}/OVMF_4M.fd
%{ovmfdir}/OVMF_CODE_4M.fd
%{ovmfdir}/OVMF_CODE_4M.ms.fd
%{ovmfdir}/OVMF_CODE_4M.secboot.fd
%{ovmfdir}/OVMF_VARS_4M.fd
%{ovmfdir}/OVMF_VARS_4M.ms.fd
%dir %{_datadir}/qemu/firmware
%{_datadir}/qemu/firmware/30-edk2-ovmf-x64-sb-enrolled.json
%{_datadir}/qemu/firmware/40-edk2-ovmf-x64-sb.json
%{_datadir}/qemu/firmware/50-edk2-ovmf-x64-nosb.json
