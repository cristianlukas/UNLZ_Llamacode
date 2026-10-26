FUNCTION _DT_INIT @ 00401000

void _DT_INIT(void)

{
  if (PTR___gmon_start___00403fe0 != (undefined *)0x0) {
    (*(code *)PTR___gmon_start___00403fe0)();
  }
  return;
}


FUNCTION __errno_location @ 00401090

/* WARNING: Unknown calling convention -- yet parameter storage is locked */

int * __errno_location(void)

{
  int *piVar1;
  
  piVar1 = (int *)(*(code *)PTR___errno_location_00404000)();
  return piVar1;
}


FUNCTION strlen @ 004010a0

/* WARNING: Unknown calling convention -- yet parameter storage is locked */

size_t strlen(char *__s)

{
  size_t sVar1;
  
  sVar1 = (*(code *)PTR_strlen_00404008)();
  return sVar1;
}


FUNCTION __stack_chk_fail @ 004010b0

void __stack_chk_fail(void)

{
  (*(code *)PTR___stack_chk_fail_00404010)();
  return;
}


FUNCTION strcmp @ 004010c0

/* WARNING: Unknown calling convention -- yet parameter storage is locked */

int strcmp(char *__s1,char *__s2)

{
  int iVar1;
  
  iVar1 = (*(code *)PTR_strcmp_00404018)();
  return iVar1;
}


FUNCTION __printf_chk @ 004010d0

void __printf_chk(void)

{
  (*(code *)PTR___printf_chk_00404020)();
  return;
}


FUNCTION strtoul @ 004010e0

/* WARNING: Unknown calling convention -- yet parameter storage is locked */

ulong strtoul(char *__nptr,char **__endptr,int __base)

{
  ulong uVar1;
  
  uVar1 = (*(code *)PTR_strtoul_00404028)();
  return uVar1;
}


FUNCTION entry @ 004011a0

void processEntry entry(undefined8 param_1,undefined8 param_2,undefined1 param_3)

{
  undefined1 auStack_8 [8];
  
  (*(code *)PTR___libc_start_main_00403fd8)(&LAB_004010f0,param_2,&param_3,0,0,param_1,auStack_8);
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}


FUNCTION FUN_004011e0 @ 004011e0

/* WARNING: Removing unreachable block (ram,0x004011ed) */
/* WARNING: Removing unreachable block (ram,0x004011f7) */

void FUN_004011e0(void)

{
  return;
}


FUNCTION FUN_00401210 @ 00401210

/* WARNING: Removing unreachable block (ram,0x0040122f) */
/* WARNING: Removing unreachable block (ram,0x00401239) */

void FUN_00401210(void)

{
  return;
}


FUNCTION _FINI_0 @ 00401250

void _FINI_0(void)

{
  if (DAT_00404040 == '\0') {
    FUN_004011e0();
    DAT_00404040 = 1;
    return;
  }
  return;
}


FUNCTION _INIT_0 @ 00401280

void _INIT_0(void)

{
  FUN_00401210();
  return;
}


FUNCTION FUN_00401290 @ 00401290

undefined4 FUN_00401290(char *param_1,ulong param_2,ulong *param_3)

{
  int *piVar1;
  ulong uVar2;
  undefined4 uVar3;
  long in_FS_OFFSET;
  char *local_38;
  long local_30;
  
  local_30 = *(long *)(in_FS_OFFSET + 0x28);
  local_38 = (char *)0x0;
  piVar1 = __errno_location();
  *piVar1 = 0;
  uVar2 = strtoul(param_1,&local_38,0);
  if (*piVar1 == 0) {
    uVar3 = 0;
    if (((local_38 != param_1) && (*local_38 == '\0')) && (uVar2 <= param_2)) {
      *param_3 = uVar2;
      uVar3 = 1;
    }
  }
  else {
    uVar3 = 0;
  }
  if (local_30 != *(long *)(in_FS_OFFSET + 0x28)) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail();
  }
  return uVar3;
}


FUNCTION FUN_00401330 @ 00401330

int FUN_00401330(char param_1,ushort param_2,uint param_3)

{
  if (param_1 == '\x10') {
    if (param_2 < 0x41) {
      return (param_3 & 1) + 0x10;
    }
    return -2;
  }
  if (param_1 != ' ') {
    return -1;
  }
  if (0x76 < (ushort)(param_2 - 2)) {
    return -3;
  }
  if ((char)(param_3 & 3) == '\x03') {
    return -4;
  }
  return (param_3 & 3) + 0x20;
}


FUNCTION FUN_00401390 @ 00401390

undefined8 FUN_00401390(int param_1,long param_2)

{
  int iVar1;
  undefined4 uVar2;
  undefined8 uVar3;
  long in_FS_OFFSET;
  undefined1 local_28 [8];
  undefined2 local_20 [4];
  undefined1 local_18 [8];
  long local_10;
  
  local_10 = *(long *)(in_FS_OFFSET + 0x28);
  if (param_1 == 5) {
    iVar1 = FUN_00401290(*(undefined8 *)(param_2 + 0x10),0xff,local_28);
    if (iVar1 != 0) {
      iVar1 = FUN_00401290(*(undefined8 *)(param_2 + 0x18),0xffff,local_20);
      if (iVar1 != 0) {
        iVar1 = FUN_00401290(*(undefined8 *)(param_2 + 0x20),0xff,local_18);
        if (iVar1 != 0) {
          uVar2 = FUN_00401330(local_28[0],local_20[0],local_18[0]);
          __printf_chk(1,&DAT_00402004,uVar2);
          uVar3 = 0;
          goto LAB_004013af;
        }
      }
    }
  }
  uVar3 = 2;
LAB_004013af:
  if (local_10 != *(long *)(in_FS_OFFSET + 0x28)) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail();
  }
  return uVar3;
}


FUNCTION FUN_00401440 @ 00401440

int FUN_00401440(uint param_1,int param_2)

{
  byte bVar1;
  byte bVar2;
  
  param_1 = param_2 * 0x1d + 0x5bU ^ param_1;
  bVar1 = (byte)param_2 & 7;
  bVar2 = (byte)param_1;
  return CONCAT31((int3)(param_1 >> 8),bVar2 << bVar1 | bVar2 >> 8 - bVar1) + 0x17;
}


FUNCTION FUN_00401460 @ 00401460

undefined8 FUN_00401460(int param_1,long param_2)

{
  undefined1 uVar1;
  int iVar2;
  undefined8 uVar3;
  long in_FS_OFFSET;
  undefined1 local_20 [8];
  undefined1 local_18 [8];
  long local_10;
  
  local_10 = *(long *)(in_FS_OFFSET + 0x28);
  if (param_1 == 4) {
    iVar2 = FUN_00401290(*(undefined8 *)(param_2 + 0x10),0xff,local_20);
    if (iVar2 != 0) {
      iVar2 = FUN_00401290(*(undefined8 *)(param_2 + 0x18),0xff,local_18);
      if (iVar2 != 0) {
        uVar1 = FUN_00401440(local_20[0],local_18[0]);
        __printf_chk(1,"0x%02x\n",uVar1);
        uVar3 = 0;
        goto LAB_0040147f;
      }
    }
  }
  uVar3 = 2;
LAB_0040147f:
  if (local_10 != *(long *)(in_FS_OFFSET + 0x28)) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail();
  }
  return uVar3;
}


FUNCTION FUN_00401500 @ 00401500

uint FUN_00401500(byte *param_1,long param_2)

{
  byte *pbVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  short sVar5;
  
  if (param_2 == 0) {
    return 0;
  }
  pbVar1 = param_1 + param_2;
  uVar3 = 0x6d3a;
  do {
    uVar3 = uVar3 ^ (uint)*param_1 << 8;
    iVar4 = 8;
    do {
      uVar2 = uVar3 * 2;
      sVar5 = (short)uVar3;
      uVar3 = uVar2;
      if (sVar5 < 0) {
        uVar3 = uVar2 ^ 0x1021;
      }
      iVar4 = iVar4 + -1;
    } while (iVar4 != 0);
    param_1 = param_1 + 1;
  } while (pbVar1 != param_1);
  return uVar3 ^ 0x6d3a;
}


FUNCTION FUN_00401550 @ 00401550

undefined8 FUN_00401550(int param_1,long param_2)

{
  undefined2 uVar1;
  int iVar2;
  size_t sVar3;
  int *piVar4;
  undefined8 uVar5;
  long lVar6;
  char *__s;
  long in_FS_OFFSET;
  ulong local_150;
  char *local_148;
  char local_13b;
  char local_13a;
  char local_139;
  undefined1 local_138 [264];
  long local_30;
  
  local_30 = *(long *)(in_FS_OFFSET + 0x28);
  if (param_1 == 3) {
    __s = *(char **)(param_2 + 0x10);
    sVar3 = strlen(__s);
    if ((sVar3 < 0x201) && ((sVar3 & 1) == 0)) {
      lVar6 = 0;
      while( true ) {
        sVar3 = strlen(__s);
        if (sVar3 <= (ulong)(lVar6 * 2)) break;
        local_13b = __s[lVar6 * 2];
        local_13a = __s[lVar6 * 2 + 1];
        local_139 = '\0';
        iVar2 = FUN_00401290(&local_13b,0xff,&local_150);
        if (iVar2 == 0) {
          local_148 = (char *)0x0;
          piVar4 = __errno_location();
          *piVar4 = 0;
          local_150 = strtoul(&local_13b,&local_148,0x10);
          if (((*piVar4 != 0) || (local_148 != &local_139)) || (0xff < local_150))
          goto LAB_00401649;
        }
        __s = *(char **)(param_2 + 0x10);
        local_138[lVar6] = (char)local_150;
        lVar6 = lVar6 + 1;
      }
      uVar1 = FUN_00401500(local_138,lVar6);
      __printf_chk(1,"0x%04x\n",uVar1);
      uVar5 = 0;
      goto LAB_00401673;
    }
  }
LAB_00401649:
  uVar5 = 2;
LAB_00401673:
  if (local_30 != *(long *)(in_FS_OFFSET + 0x28)) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail();
  }
  return uVar5;
}


FUNCTION FUN_004016a0 @ 004016a0

int FUN_004016a0(char param_1,char param_2)

{
  int iVar1;
  
  if ((param_1 != '\0') || (iVar1 = 1, param_2 != '\x01')) {
    if (((param_2 != '\x02') || (iVar1 = 2, param_1 != '\x01')) &&
       ((param_2 != '\x03' || (iVar1 = 0, param_1 != '\x01')))) {
      return (param_2 == '\x04' && param_1 == '\x02') - 1;
    }
  }
  return iVar1;
}


FUNCTION FUN_004016f0 @ 004016f0

undefined8 FUN_004016f0(int param_1,long param_2)

{
  int iVar1;
  undefined4 uVar2;
  undefined8 uVar3;
  long in_FS_OFFSET;
  undefined1 local_20 [8];
  undefined1 local_18 [8];
  long local_10;
  
  local_10 = *(long *)(in_FS_OFFSET + 0x28);
  if (param_1 == 4) {
    iVar1 = FUN_00401290(*(undefined8 *)(param_2 + 0x10),0xff,local_20);
    if (iVar1 != 0) {
      iVar1 = FUN_00401290(*(undefined8 *)(param_2 + 0x18),0xff,local_18);
      if (iVar1 != 0) {
        uVar2 = FUN_004016a0(local_20[0],local_18[0]);
        __printf_chk(1,&DAT_00402004,uVar2);
        uVar3 = 0;
        goto LAB_0040170f;
      }
    }
  }
  uVar3 = 2;
LAB_0040170f:
  if (local_10 != *(long *)(in_FS_OFFSET + 0x28)) {
                    /* WARNING: Subroutine does not return */
    __stack_chk_fail();
  }
  return uVar3;
}


FUNCTION _DT_FINI @ 00401784

void _DT_FINI(void)

{
  return;
}


FUNCTION __libc_start_main @ 00405000

/* WARNING: Control flow encountered bad instruction data */

void __libc_start_main(void)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


FUNCTION __errno_location @ 00405008

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Unknown calling convention -- yet parameter storage is locked */

int * __errno_location(void)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


FUNCTION strlen @ 00405010

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Unknown calling convention -- yet parameter storage is locked */

size_t strlen(char *__s)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


FUNCTION __stack_chk_fail @ 00405018

/* WARNING: Control flow encountered bad instruction data */

void __stack_chk_fail(void)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


FUNCTION strcmp @ 00405020

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Unknown calling convention -- yet parameter storage is locked */

int strcmp(char *__s1,char *__s2)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


FUNCTION __gmon_start__ @ 00405028

/* WARNING: Control flow encountered bad instruction data */

void __gmon_start__(void)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


FUNCTION __printf_chk @ 00405030

/* WARNING: Control flow encountered bad instruction data */

void __printf_chk(void)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


FUNCTION strtoul @ 00405038

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Unknown calling convention -- yet parameter storage is locked */

ulong strtoul(char *__nptr,char **__endptr,int __base)

{
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


