#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <sys/time.h>
#include <sys/resource.h>

#include "jhjr_math.h"


#define	BIN_FILENAME	argv[0]
#define	NVAR_MAX	512
#define	IFILENAME	1
#define	OFILENAME	2


struct clause_te {
	unsigned int	v1;
	unsigned int	v2;
	unsigned int	v3;
	unsigned int	inv;
} clause_te;

int			n_var;
int			n_clause;
integer_t *		one;
integer_t *		negativeone;
integer_t *		zero;
integer_t *		eval_t0;
integer_t *		eval_t1;
istack_t *		S;
int			status_report;


int			main(int,char **);
int			parseoptions(int,char **,char **);
int			clause_compar(const void *,const void *);
int			clause_count(struct clause_te *,int);
static inline int	EVAL1(integer_t *,struct clause_te *);
static inline int	EVAL2(integer_t *,struct clause_te *);
static inline int	EVAL3(integer_t *,struct clause_te *);
void			solve(struct clause_te *,int);
void			status(int);
void			dump(struct clause_te *,int);
void			freeze(struct clause_te *,int,int,FILE *);
int			choose(int,int);
long long		ipow(int,int);
size_t			strcnt(const char *,char);


int
main(int argc,char ** argv)
{
	struct clause_te *	psi=NULL;
	struct clause_te *	scratch=NULL;
	unsigned int		scr_v1;
	unsigned int		scr_v2;
	unsigned int		scr_v3;
	int			c;
	int			i,j;
	struct rusage		usage[2];
	char *			filename=NULL;
	FILE *			ifp=NULL;
	FILE *			ofp=NULL;
	int			optval;

	if (0>(optval=parseoptions(argc,argv,&filename))) {
		exit(1);
	}
	if (IFILENAME==optval) {
		if (0==strcmp(filename,"-")) {
			ifp=stdin;
		} else {
			ifp=fopen(filename,"r");
			if (NULL==ifp) {
				fprintf(stderr,"%s: Cannot open "
					       "'%s' for obtaining "
						"Boolean expression.\n",
					BIN_FILENAME,filename);
				exit(1);
			} 
			fscanf(ifp,"%d %d", &n_var, &n_clause);
			assert(n_var>=3);
			assert(n_clause<=8*choose(n_var,3));
			psi=(struct clause_te *)malloc(sizeof(struct clause_te)*n_clause);
			if (psi==NULL) {
				fprintf(stderr,"Cannot malloc() psi!\n");
				exit(2);
			}

			for(j=0;j<n_clause;j++) {
				struct clause_te * p;

				p=psi+j;
				fscanf(ifp,"%x %x %x %x",
					&(p->v1),
					&(p->v2),
					&(p->v3),
					&(p->inv));
			}
			fclose(ifp);
			ifp=NULL;
//			getrusage(RUSAGE_SELF,&usage[0]);

			goto do_solve;
		}
	} else {
		if (n_var<3) {
			fprintf(stderr,"%s: n_var must be >= 3!\n",
				BIN_FILENAME);
			exit(1);
		}
		if ((n_clause<1) || (n_clause>(8*choose(n_var,3)))) {
			fprintf(stderr,"%s: n_clause must be "
				       "[1,8*binom(n_var,3)]!\n",
				BIN_FILENAME);
			exit(1);
		} else {
			printf("main(): MAX(n_clause) = %d\n",8*choose(n_var,3));
		}
	} 
	if (OFILENAME==optval) {
		if (0==strcmp(filename,"-")) {
			ofp=stdout;
		} else {
			ofp=fopen(argv[4],"w");
			if (NULL==ofp) {
				fprintf(stderr,"%s: Cannot open "
					       "'%s' for storing "
						"Boolean expression.\n",
					BIN_FILENAME,argv[4]);
				exit(1);
			}
		}
	}

#if defined(DEBUG)
	{
		integer_t *	tmp;
		integer_t *	scratch;

		tmp=mkinteger(NVAR_MAX,0xdeadbeef);
		assert(tmp);
		scratch=mkinteger(NVAR_MAX,0);
		assert(scratch);

		printf("main(): tmp = 0x");
		jhjr_puts(tmp);
		printf("\n");

		printf("main(): (tmp<<=8) = 0x");
		cpinteger(scratch,tmp);
		jhjr_sll(scratch,scratch,8);
		jhjr_puts(scratch);
		printf("\n");

		printf("main(): logical(tmp>>=8) = 0x");
		cpinteger(scratch,tmp);
		jhjr_srl(scratch,scratch,8);
		jhjr_puts(scratch);
		printf("\n");

		printf("main(): arithmatic(tmp>>=8) = 0x");
		cpinteger(scratch,tmp);
		jhjr_sra(scratch,scratch,8);
		jhjr_puts(scratch);
		printf("\n");

		rminteger(tmp);
		rminteger(scratch);

		exit(0);
	}
#endif

	psi=(struct clause_te *)malloc(sizeof(struct clause_te)*n_clause);
	if (psi==NULL) {
		fprintf(stderr,"Cannot malloc() psi!\n");
		exit(2);
	}

	scratch=(struct clause_te *)malloc(sizeof(struct clause_te)*8*choose(n_var,3));
	scr_v1=1;
	scr_v2=2;
	scr_v3=3;
	for(i=0;i<8*choose(n_var,3);i+=8) {
		int	j;

		for(j=0;j<8;j++) {
			scratch[i+j].inv=j;
			scratch[i+j].v1=scr_v1;
			scratch[i+j].v2=scr_v2;
			scratch[i+j].v3=scr_v3;
		}

		scr_v3+=1;
		if (scr_v3>n_var) {
			scr_v2+=1;
			if (scr_v2>n_var-1) {
				scr_v1+=1;
				scr_v2=scr_v1+1;
			}
			scr_v3=scr_v2+1;
		}
	}

	c=8*choose(n_var,3);
	i=0;
	while (n_clause!=c) {
		if (!(scratch[i].inv&0x80000000) && (rand()&0x1)) {
			scratch[i].inv=0x80000000;
			c-=1;
		}
		i+=1;
		i%=8*choose(n_var,3);
	}
	j=0;
	for(i=0;i<8*choose(n_var,3);i++) {
		if (!(scratch[i].inv&0x80000000)) {
			psi[j].v1=scratch[i].v1;
			psi[j].v2=scratch[i].v2;
			psi[j].v3=scratch[i].v3;
			psi[j].inv=scratch[i].inv;
			j+=1;
		}
	}
#if defined(DEBUG)
	printf("psi =\n");
	dump(psi,n_clause);
#endif
//	getrusage(RUSAGE_SELF,&usage[0]);
//	printf("main(): getrusage() -> %15ld %15ld\n",
//		(1000000*usage[0].ru_utime.tv_sec+usage[0].ru_utime.tv_usec),
//		(1000000*usage[0].ru_stime.tv_sec+usage[0].ru_stime.tv_usec));
	qsort(psi,n_clause,sizeof(struct clause_te),clause_compar);

	if (ofp) {
		freeze(psi,n_var,n_clause,ofp);
		fclose(ofp);
		ofp=NULL;
	}

do_solve:
/* initialize globally useful interger_t variables... */
	one=mkinteger(NVAR_MAX,1);
	negativeone=mkinteger(NVAR_MAX,-1);
	zero=mkinteger(NVAR_MAX,0);
	eval_t0=mkinteger(NVAR_MAX,0);
	eval_t1=mkinteger(NVAR_MAX,0);
	S=mkstack(NVAR_MAX,64);
	ststack(S);
	status_report=0;

	if (clause_count(psi,n_var)) {
		goto done;
	}
	assert(signal(SIGUSR1,status)!=SIG_ERR);
	printf("main(): starting solve()...\n");
	solve(psi,n_var);
//	getrusage(RUSAGE_SELF,&usage[1]);
//	printf("main(): getrusage() -> %15ld %15ld\n",
//		((1000000*usage[1].ru_utime.tv_sec+usage[1].ru_utime.tv_usec)-
//		 (1000000*usage[0].ru_utime.tv_sec+usage[0].ru_utime.tv_usec)),
//		((1000000*usage[1].ru_stime.tv_sec+usage[1].ru_stime.tv_usec)-
//		 (1000000*usage[0].ru_stime.tv_sec+usage[0].ru_stime.tv_usec)));

done:
	if (filename) {
		free(filename);
	}
	rminteger(one);
	rminteger(negativeone);
	rminteger(zero);
	rminteger(eval_t0);
	rminteger(eval_t1);
	rmstack(S);

	fflush(NULL);

	return	0;
}

int
parseoptions(int argc,char ** argv,char ** filename)
{
	int	retval=0;

	assert(NULL==*filename);

	if (argc<3) {
		goto fail;
	}
	if ((argv[1][0] < '0') || (argv[1][0] > '9')) {
		if (0==strcmp(argv[1],"-i")) {
			*filename=strdup(argv[2]);
			retval=IFILENAME;
		} else {
			goto fail;
		}
	} else {
		n_var=atoi(argv[1]);
		n_clause=atoi(argv[2]);
		if (argc!=3) {
			if (argc==5) {
				if (0==strcmp(argv[3],"-o")) {
					*filename=strdup(argv[4]);
					retval=OFILENAME;
				} else {
					goto fail;
				}
			} else {
				goto fail;
			}
		}
	}

	return retval;
fail:
	fprintf(stderr,
		"usage: %s n_var n_clause [-o filename]\n"
		"       %s -i filename\n",
		BIN_FILENAME,
		BIN_FILENAME);

	return -1;
}


/* will yield decending-order sort when
 * used in conjuction with qsort()...
 */
int clause_compar(const void * a,const void * b)
{
	struct clause_te * p=(struct clause_te *)a;
	struct clause_te * q=(struct clause_te *)b;

	if (p->v1<q->v1)
		return 1;
	else
	if (p->v1>q->v1)
		return -1;
	else
	if (p->v2<q->v2)
		return 1;
	else
	if (p->v2>q->v2)
		return -1;
	else
	if (p->v3<q->v3)
		return 1;
	else
	if (p->v3>q->v3)
		return -1;
	else
		return 0;
}

int
clause_count(struct clause_te * psi,int n)
{
	int 			i,j=0;
	struct clause_te *	p=psi;
	unsigned int *		count;
	unsigned int		v1;
	unsigned int		v2;
	unsigned int		v3;
	struct clause_te *	tmp;

	tmp=(struct clause_te *)malloc(sizeof(struct clause_te)*8);
	memset((void *)tmp,0,sizeof(struct clause_te)*8);

	if (!psi)
		return 0;

	count=(unsigned int *)malloc(sizeof(unsigned int)*choose(n,3));
	if (!count) {
		fprintf(stderr,
			"clause_count(): Cannot malloc() 'count'!\n");
		exit(1);
	}
	memset((void *)count,0,sizeof(unsigned int)*choose(n,3));
	v1=p->v1;
	v2=p->v2;
	v3=p->v3;
	for (i=0;i<n_clause;i++) {
		p=psi+i;
		if ((v1==p->v1) && (v2==p->v2) && (v3==p->v3)) {
			tmp[count[j]].v1=p->v1;
			tmp[count[j]].v2=p->v1;
			tmp[count[j]].v3=p->v1;
			tmp[count[j]].inv=p->inv;
			count[j]+=1;
		} else {
			j+=1;
			count[j]+=1;
			v1=p->v1;
			v2=p->v2;
			v3=p->v3;
			tmp[0].v1=p->v1;
			tmp[0].v2=p->v1;
			tmp[0].v3=p->v1;
			tmp[0].inv=p->inv;
		}

		if (count[j]==8) {
			printf("clause_count(): Perfect logical contradiction...\n");
			dump(tmp,8);
			free(tmp);
			printf("clause_count(): Boolean expression is trivially unsatisfiable!\n");

			return 1;
		}
	}

	free(tmp);

	return 0;
}


static inline int
EVAL1(integer_t * s,struct clause_te * p)
{
	int	p0,p1,p2,p3;

	jhjr_srl(eval_t0,s,(p->v1)-1);
	jhjr_and(eval_t1,eval_t0,one);
	p2=1-jhjr_eq(eval_t1,zero);
	p0=p2 && !(p->inv & 1);
	p3=1-p2;
	p1=p3 &&  (p->inv & 1);

	return p0 || p1;
}

static inline int
EVAL2(integer_t * s,struct clause_te * p)
{
	int	p0,p1,p2,p3;

	jhjr_srl(eval_t0,s,(p->v2)-1);
	jhjr_and(eval_t1,eval_t0,one);
	p2=1-jhjr_eq(eval_t1,zero);
	p0=p2 && !(p->inv & 2);
	p3=1-p2;
	p1=p3 &&  (p->inv & 2);

	return p0 || p1;
}

static inline int
EVAL3(integer_t * s,struct clause_te * p)
{
	int	p0,p1,p2,p3;

	jhjr_srl(eval_t0,s,(p->v3)-1);
	jhjr_and(eval_t1,eval_t0,one);
	p2=1-jhjr_eq(eval_t1,zero);
	p0=p2 && !(p->inv & 4);
	p3=1-p2;
	p1=p3 &&  (p->inv & 4);

	return p0 || p1;
}

void
solve(struct clause_te * psi,int n)
{
	struct clause_te *	p;
	integer_t *	 	s;
	integer_t *		s_max;
	integer_t *		allones;
	int			eval=0;
	int			partition=0;
	integer_t **		mask;
	integer_t **		incr;
	int			k;

	s=mkinteger(NVAR_MAX,0);
	s_max=mkinteger(NVAR_MAX,1);
	jhjr_sll(s_max,s_max,(unsigned int)n);
	allones=mkinteger(NVAR_MAX,-1);
	mask=(integer_t **)malloc(sizeof(integer_t *)*n_var);
	incr=(integer_t **)malloc(sizeof(integer_t *)*n_var);
	for(k=0;k<n_var;k++) {
		mask[k]=mkinteger(NVAR_MAX,0);
		cpinteger(mask[k],allones);
		jhjr_sll(mask[k],mask[k],k);
		incr[k]=mkinteger(NVAR_MAX,1);
		jhjr_sll(incr[k],incr[k],k);
	}
	while (jhjr_lt(s,s_max)) {
		int	i;

		eval=1;
		for(i=0;i<n_clause;i++) {
			p=psi+i;
			eval&=((EVAL1(s,p)||EVAL2(s,p)||EVAL3(s,p)) ? 1 : 0);
			if (eval==0)
				break;
		}
		if (eval) {
			printf("solve(): [SOLUTION] s = ");
			jhjr_puts(s);
			printf("\n");
			jhjr_add(s,s,one);
		} else {
			partition+=1;
			if (status_report) {
				status_report=0;
				printf("solve(): [STATUS REPORT] s = ");
				jhjr_puts(s);
				printf("\n");
			}
			jhjr_and(s,s,mask[(p->v1-1)]);
			jhjr_add(s,s,incr[(p->v1-1)]);
#if defined(DEBUG)
printf("solve(): partition = %9d:0x",partition);
jhjr_puts(s);
puts("");
#endif
		}
	}
	for(k=0;k<n_var;k++) {
		rminteger(mask[k]);
		rminteger(incr[k]);
	}
	free(mask);
	free(incr);
	rminteger(s_max);
	rminteger(s);
}


void
status(int N)
{
	status_report=1;
}

/*
 * NOTE: dump() assumes 80 characters/line of text... can't
 * be bothered with variable terminal widths just now.
 */
void
dump(struct clause_te * psi,int n_clause)
{
	struct clause_te *	p;
	char			tmp[256];
	int			j,i=0;

	if (!n_clause)
		return;

	for(j=0;j<n_clause;j++) {
		p=psi+j;

		memset((void *)tmp,0,256);
		sprintf(tmp+strlen(tmp),"(");
		if (p->inv & 1)
			sprintf(tmp+strlen(tmp),"\\");
		sprintf(tmp+strlen(tmp),"%c",'a'+(((p->v1-1)&0xf0)>>4));
		sprintf(tmp+strlen(tmp),"%c +",'a'+(((p->v1-1)&0x0f)>>0));
		sprintf(tmp+strlen(tmp)," ");
		if (p->inv & 2)
			sprintf(tmp+strlen(tmp),"\\");
		sprintf(tmp+strlen(tmp),"%c",'a'+(((p->v2-1)&0xf0)>>4));
		sprintf(tmp+strlen(tmp),"%c +",'a'+(((p->v2-1)&0x0f)>>0));
		sprintf(tmp+strlen(tmp)," ");
		if (p->inv & 4)
			sprintf(tmp+strlen(tmp),"\\");
		sprintf(tmp+strlen(tmp),"%c",'a'+(((p->v3-1)&0xf0)>>4));
		sprintf(tmp+strlen(tmp),"%c",'a'+(((p->v3-1)&0x0f)>>0));
		sprintf(tmp+strlen(tmp),")");

		if (i==0) {
			printf("\t");
		} else
		if (i==4) {
			printf("\n\t");
			i=0; /* ...b/c only 4 clauses fit/80-byte text line */
		}
		i++;
		printf("%s",tmp);
	}
	printf("\n");
}

void
freeze(struct clause_te * psi,int n_var,int n_clause,FILE * fp)
{
	struct clause_te *	p;
	int			j;

	assert(NULL!=fp);

	if (!n_clause)
		return;

	fprintf(fp,"%d %d\n",n_var,n_clause);
	for(j=0;j<n_clause;j++) {
		p=psi+j;
		fprintf(fp,"%08x %08x %08x %x\n",p->v1,p->v2,p->v3,p->inv);
	}
}


int
choose(int n,int r)
{
	int	numerator=1;
	int	denominator=1;
	int	q=((n-r < r) ? (n-r) : r);
	int	i;

	for(i=0;i<q;i++) {
		numerator*=(n-i);
		denominator*=(q-i);
	}

	return (numerator/denominator);
}

long long
ipow(int x,int y)
{
	int	retval=1;
	int	i=0;

	if (!y)
		return retval;
	else
	if (y & 1)
		retval*=x;

	y>>=1;
	while (y) {
		int	j;
		int	ntrm=x;

		i++;
		if (y & 1) {
			for(j=0;j<i;j++)
				ntrm*=ntrm;
		} else {
			ntrm=1;
		}
		y>>=1;
		retval*=ntrm;
	}

	return retval;	
}

size_t
strcnt(const char * s,char c)
{
	size_t	count=0;
	int	i;

	for(i=0;s[i]!=0;i++)
		if (s[i]==c) count++;

	return count;
}
