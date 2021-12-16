
#include "m_pd.h"

#define GET_OBJ(val) (t_pd *)gensym(val)->s_thing


void dsp_on() {
    t_atom av[1];
    SETFLOAT(av, (t_float)1);
    pd_typedmess((t_pd *)gensym("pd")->s_thing, gensym("dsp"), 1, av2);	
}
