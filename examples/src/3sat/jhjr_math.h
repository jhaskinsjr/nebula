/* jhjr_math.h */


typedef struct integer_st {
	unsigned int	nbits;
	unsigned int	nbytes;
	unsigned char *	data;
} integer_t;

typedef struct istack_st {
	unsigned int	nelem;
	unsigned int	nbits;
	unsigned int	nbytes;
	unsigned int	tosptr;
	integer_t **	block;
} istack_t;

#define	JHJR_SUCCESS		0
#define	JHJR_OVERFLOW		1
#define	JHJR_OPERANDMISMATCH	2
#define	JHJR_INVALIDOPERATOR	4

#define	JHJR_OP_AND		0
#define	JHJR_OP_OR		1
#define	JHJR_OP_XOR		2
#define	JHJR_OP_NOT		3
#define	JHJR_OP_SLL		4
#define	JHJR_OP_SRL		5
#define	JHJR_OP_SRA		6


integer_t *	mkinteger(unsigned int,int);
void		rminteger(integer_t *);
int		cpinteger(integer_t *,integer_t *);
void		stinteger(integer_t *,int);
istack_t *	mkstack(unsigned int,unsigned int);
void		rmstack(istack_t *);
void		ststack(istack_t *);
int		jhjr_add(integer_t *,integer_t *,integer_t *);
#if 0
int		jhjr_sub(integer_t *,integer_t *,integer_t *);
#endif
int		jhjr_shift(integer_t *,integer_t *,unsigned int,unsigned char);
#define		jhjr_sll(d,s,N)		jhjr_shift(d,s,N,JHJR_OP_SLL)
#define		jhjr_srl(d,s,N)		jhjr_shift(d,s,N,JHJR_OP_SRL)
#define		jhjr_sra(d,s,N)		jhjr_shift(d,s,N,JHJR_OP_SRA)
int		jhjr_bitop(integer_t *,integer_t *,integer_t *,unsigned char);
#define		jhjr_and(d,s0,s1)	jhjr_bitop(d,s0,s1,JHJR_OP_AND)
#define		jhjr_or(d,s0,s1)	jhjr_bitop(d,s0,s1,JHJR_OP_OR)
#define		jhjr_xor(d,s0,s1)	jhjr_bitop(d,s0,s1,JHJR_OP_XOR)
#define		jhjr_not(d,s0)		jhjr_bitop(d,s0,NULL,JHJR_OP_NOT)
int		jhjr_compar(integer_t *,integer_t *);
#define		jhjr_eq(s0,s1)		(jhjr_compar(s0,s1)==0)
#define		jhjr_lt(s0,s1)		(jhjr_compar(s0,s1)==-1)
#define		jhjr_gt(s0,s1)		(jhjr_compar(s0,s1)==1)
#define		jhjr_le(s0,s1)		(jhjr_eq(s0,s1) || jhjr_lt(s0,s1))
#define		jhjr_ge(s0,s1)		(jhjr_eq(s0,s1) || jhjr_gt(s0,s1))
void		jhjr_dump(integer_t *);
void		jhjr_puts(integer_t *);
