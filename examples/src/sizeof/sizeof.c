#include <stdio.h>
#include <stdlib.h>


int main(void);


int
main(void)
{
	printf("sizeof(char)        : %d\n", sizeof(char));
	printf("sizeof(short)       : %d\n", sizeof(short));
	printf("sizeof(int)         : %d\n", sizeof(int));
	printf("sizeof(long)        : %d\n", sizeof(long));
	printf("sizeof(long int)    : %d\n", sizeof(long int));
	printf("sizeof(long long)   : %d\n", sizeof(long long));
	printf("sizeof(float)       : %d\n", sizeof(float));
	printf("sizeof(double)      : %d\n", sizeof(double));
	printf("sizeof(long double) : %d\n", sizeof(long double));
	return 0;
}
