#include <stdio.h>
#include <stdlib.h>

int main(int, char **);

int
main(int argc, char ** argv)
{
	int retval = 0;
	int x = 1;
	for (; x < argc; x+= 1) retval += atoi(argv[x]);
	return retval;
//	int retval = 0;
//	int x = 1;
//	retval += atoi(argv[x]); x += 1;
//	retval += atoi(argv[x]); x += 1;
//	retval += atoi(argv[x]); x += 1;
//	retval += atoi(argv[x]); x += 1;
//	int x = 1;
//	int retval = atoi(argv[x]);
//	return retval;
}
