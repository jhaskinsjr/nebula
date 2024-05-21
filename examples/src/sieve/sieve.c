#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

int
main(int argc, char ** argv)
{
    int N = atoi(argv[1]);
    bool * prime = (bool *)malloc((1 + N) * sizeof(bool));
    for (int x = 0; x < (1 + N); x += 1) prime[x] = true;
    for (int p = 2; p * p <= N; p += 1) {
        if (prime[p]) {
            for (int y = p * p; y <= N; y += p) prime[y] = false;
        }
    }
    for (int p = 2; p <= N; p += 1) {
        if (prime[p]) printf("%d ", p);
    }
    printf("\n");
    free(prime);
    return 0;
}