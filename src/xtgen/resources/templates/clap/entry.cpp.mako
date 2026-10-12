/* ${e.name}_entry.cpp

Exports clap_entry from the functions in ${e.name}.c. clap-wrapper compiles
this file once per plugin format.

*/

#include <clap/clap.h>

extern "C" {
bool ${e.name}_entry_init(const char *plugin_path);
void ${e.name}_entry_deinit(void);
const void *${e.name}_entry_get_factory(const char *factory_id);

CLAP_EXPORT extern const clap_plugin_entry_t clap_entry;
const clap_plugin_entry_t clap_entry = {
    CLAP_VERSION_INIT,
    ${e.name}_entry_init,
    ${e.name}_entry_deinit,
    ${e.name}_entry_get_factory,
};
}
