#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>


int main(void);


int
main(void)
{
	struct stat	statbuf;

	printf("sizeof(char)                     : %d\n", sizeof(char));
	printf("sizeof(short)                    : %d\n", sizeof(short));
	printf("sizeof(int)                      : %d\n", sizeof(int));
	printf("sizeof(long)                     : %d\n", sizeof(long));
	printf("sizeof(long int)                 : %d\n", sizeof(long int));
	printf("sizeof(long long)                : %d\n", sizeof(long long));
	printf("sizeof(float)                    : %d\n", sizeof(float));
	printf("sizeof(double)                   : %d\n", sizeof(double));
	printf("sizeof(long double)              : %d\n", sizeof(long double));
	puts("---");
	printf("sizeof(statbuf)                  : %d\n", sizeof(statbuf));
	printf("sizeof(statbuf.st_dev)           : %d\n", sizeof(statbuf.st_dev));
	printf("sizeof(statbuf.st_ino)           : %d\n", sizeof(statbuf.st_ino));
	printf("sizeof(statbuf.st_mode)          : %d\n", sizeof(statbuf.st_mode));
	printf("sizeof(statbuf.st_nlink)         : %d\n", sizeof(statbuf.st_nlink));
	printf("sizeof(statbuf.st_uid)           : %d\n", sizeof(statbuf.st_uid));
	printf("sizeof(statbuf.st_gid)           : %d\n", sizeof(statbuf.st_gid));
	printf("sizeof(statbuf.st_rdev)          : %d\n", sizeof(statbuf.st_rdev));
	printf("sizeof(statbuf.st_size)          : %d\n", sizeof(statbuf.st_size));
	printf("sizeof(statbuf.st_atime)         : %d\n", sizeof(statbuf.st_atime));
	printf("sizeof(statbuf.st_mtime)         : %d\n", sizeof(statbuf.st_mtime));
	printf("sizeof(statbuf.st_ctime)         : %d\n", sizeof(statbuf.st_ctime));
	printf("sizeof(statbuf.st_atim)          : %d\n", sizeof(statbuf.st_atim));
	printf("sizeof(statbuf.st_mtim)          : %d\n", sizeof(statbuf.st_mtim));
	printf("sizeof(statbuf.st_ctim)          : %d\n", sizeof(statbuf.st_ctim));
	printf("sizeof(statbuf.st_blksize)       : %d\n", sizeof(statbuf.st_blksize));
	printf("sizeof(statbuf.st_blocks)        : %d\n", sizeof(statbuf.st_blocks));
	printf("sizeof(statbuf.st_spare4)        : %d\n", sizeof(statbuf.st_spare4));
	puts("---");
	printf("S_IFREG                          : %d\n", S_IFREG);
	printf("O_CREAT                          : %d\n", O_CREAT);
	puts("---");
	memset((void *)&statbuf, 0, sizeof(statbuf));
	*((unsigned short *)(&statbuf.st_dev)) = 0x1111;
	*((unsigned short *)(&statbuf.st_ino)) = 0x2222;
	*((unsigned int *)(&statbuf.st_mode)) = 0x33333333;
	*((unsigned short *)(&statbuf.st_nlink)) = 0x4444;
	*((unsigned short *)(&statbuf.st_uid)) = 0x5555;
	*((unsigned short *)(&statbuf.st_gid)) = 0x6666;
	*((unsigned short *)(&statbuf.st_rdev)) = 0x7777;
	*((unsigned long *)(&statbuf.st_size)) = 0x8888888888888888;
	for (int x = 0; x < sizeof(statbuf); x += 1) printf("%02x", ((unsigned char *)(&statbuf))[x]); 
	puts("");

	return 0;
}
