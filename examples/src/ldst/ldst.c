// sample code to test servicing LD instructions from queued ST instructions

#include <stdio.h>

int
main(void)
{
    volatile int x = 0;
    for(int a = 0; a < 11 ; a += 1) x += 1;
    return 0;
}