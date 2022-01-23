/* ${e.name}.c

${e.meta['desc']}

Features:
% for feature in e.meta['features']:
- ${feature}
% endfor

Author: ${e.meta['author']}
Repo: ${e.meta['repo']}

*/

#include "m_pd.h"

/*
 * ${e.name} class object
 * ---------------------------------------------------------------------------
 */

static t_class *${e.name}_tilde_class;


/*
 * ${e.name} class struct (data-space)
 * ---------------------------------------------------------------------------
 */

typedef struct _${e.name}_tilde {
    t_object x_obj;
    t_float x_f; // main signal in

    /* parameters */
    % for p in e.params:
    ${p.struct_declaration};
    % endfor

    /* outlets */
    % for o in e.outlets:
    t_outlet *out_${o.name};
    % endfor
} t_${e.name}_tilde;


/*
 * ${e.name} class methods (operation-space)
 * ---------------------------------------------------------------------------
 */

// typed-methods
% for method in e.type_methods:
void ${e.name}_tilde_${method.type}(${method.args})
{
    post("${method.type} body");
}

% endfor

// message-methods
% for method in e.message_methods:
void ${e.name}_tilde_${method.name}(${method.args})
{
    % if method.doc:
    // ${method.doc}
    % endif
    post("${method.name} body");
}

% endfor

/*
 * ${e.name} dsp operaitions
 * ---------------------------------------------------------------------------
 */


t_int *${e.name}_tilde_perform(t_int *w)
{
  /* the first element is a pointer to the dataspace of this object */
  t_xfade_tilde *x = (t_xfade_tilde *)(w[1]);
  /* here is a pointer to the t_sample arrays that hold the 2 input signals */
  t_sample    *in1 =      (t_sample *)(w[2]);
  t_sample    *in2 =      (t_sample *)(w[3]);
  /* here comes the signalblock that will hold the output signal */
  t_sample    *out =      (t_sample *)(w[4]);
  /* all signalblocks are of the same length */
  int            n =             (int)(w[5]);
  /* get (and clip) the mixing-factor */
  t_sample pan = (x->x_pan<0)?0.0:(x->x_pan>1)?1.0:x->x_pan;
  /* just a counter */
  int i;

  /* this is the main routine:
   * mix the 2 input signals into the output signal
   */
  for(i=0; i<n; i++)
    {
      out[i]=in1[i]*(1-pan)+in2[i]*pan;
    }

  /* return a pointer to the dataspace for the next dsp-object */
  return (w+6);
}


/**
 * register a special perform-routine at the dsp-engine
 * this function gets called whenever the DSP is turned ON
 * the name of this function is registered in xfade_tilde_setup()
 */
void ${e.name}_tilde_dsp(t_xfade_tilde *x, t_signal **sp)
{
  /* add xfade_tilde_perform() to the DSP-tree;
   * the xfade_tilde_perform() will expect "5" arguments (packed into an
   * t_int-array), which are:
   * the objects data-space, 3 signal vectors (which happen to be
   * 2 input signals and 1 output signal) and the length of the
   * signal vectors (all vectors are of the same length)
   */
  dsp_add(${e.name}_tilde_perform, 5, x,
          sp[0]->s_vec, sp[1]->s_vec, sp[2]->s_vec, sp[0]->s_n);
}


/*
 * ${e.name} class destructor
 * ---------------------------------------------------------------------------
 */


/**
 * this is the "destructor" of the class;
 * it allows us to free dynamically allocated ressources
 */
void ${e.name}_tilde_free(t_${e.name}_tilde *x)
{
  /* free any ressources associated with the given inlet */
  inlet_free(x->x_in2);
  inlet_free(x->x_in3);

  /* free any ressources associated with the given outlet */
  outlet_free(x->x_out);
}


/*
 * ${e.name} class constructor
 * ---------------------------------------------------------------------------
 */

void *${e.name}_tilde_new(${e.class_new_args})
{
    t_${e.name}_tilde *x = (t_${e.name}_tilde *)pd_new(${e.name}_tilde_class);

    // initialize variables
    % for p in e.params:
    x->${p.name} = ${p.initial};
    % endfor

    // populate variables
    % if len(e.args) > 0:
    // switch stmt here
    % endif

    // create inlets
    // inlet_new(&x->x_obj, &x->x_obj.ob_pd, gensym("list"), gensym("bound"));
    % for i in e.inlets:
    ${i.type}inlet_new(&x->x_obj, &x->${i.name});
    % endfor

    // initialize outlets
    % for o in e.outlets:
    x->out_${o.name} = outlet_new(&x->x_obj, &s_${o.type});
    % endfor

    return (void *)x;
}





/*
 * ${e.name} class setup
 * ---------------------------------------------------------------------------
 */

void ${e.name}_tilde_setup(void) 
{
    ${e.name}_tilde_class = class_new(gensym("${e.name}~"),
                            (t_newmethod)${e.name}_tilde_new,
                            ${e.name}_tilde_free,
                            sizeof(t_${e.name}_tilde),
                            CLASS_DEFAULT,
                            ${e.class_type_signature});

    // typed methods
    %for m in e.type_methods:
    ${m.class_addmethod};
    % endfor

    // message methods
    %for m in e.message_methods:
    ${m.class_addmethod};
    % endfor

    // set main signal in
    CLASS_MAINSIGNALIN(${e.name}_tilde_class, ${e.name}_tilde, x_f);

    /* Bind the DSP method, which is called when the DACs are turned on */
    class_addmethod(${e.name}_tilde_class, (t_method){e.name}_tilde_dsp, gensym("dsp"), 0);

    % if e.alias:
    // set the alias to external
    ${e.class_addcreator};
    % endif

    // set name of default help file
    class_sethelpsymbol(${e.name}_tilde_class, gensym("${e.help}"));
}

