// return the -1 * argv[1]

#include <stdio.h>
#include <stdlib.h>

int
main(int argc, char ** argv)
{
	return -1 * ((argc > 1) ? (int)atoi(argv[1]) : 0);
}
