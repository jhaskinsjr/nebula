int
atoi(const char * s)
{
	int retval = 0;
	int x = ('-' == s[0]) ? 1 : 0;
	while (s[x] >= '0' && s[x] <= '9') {
		retval *= 10;
		retval += s[x] - '0';
		x += 1;
	}
	return (('-' == s[0]) ? 0 - retval : 0 + retval);
}