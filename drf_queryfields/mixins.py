class MisconfiguredSerializer(Exception):
    pass

class QueryFieldsMixin(object):

    # If using Django filters in the API, these labels mustn't conflict with any model field names.
    include_arg_name = 'fields'
    exclude_arg_name = 'fields!'

    # Split field names by this string.  It doesn't necessarily have to be a single character.
    # Avoid RFC 1738 reserved characters i.e. ';', '/', '?', ':', '@', '=' and '&'
    delimiter = ','

    def __init__(self, *args, **kwargs):
        force_fields = kwargs.pop('fields', None)
        super(QueryFieldsMixin, self).__init__(*args, **kwargs)

        if force_fields:
            for field in self.fields.keys():
                if field not in force_fields:
                    self.fields.pop(field)
            return

        try:
            request = self.get_request()
        except MisconfiguredSerializer as exc:
            return

        method = self.get_method(request)
        if method != 'GET':
            return

        query_params = self.get_query_params(request)

        includes = query_params.getlist(self.include_arg_name)
        include_field_names = {name for names in includes for name in names.split(self.delimiter) if name}

        excludes = query_params.getlist(self.exclude_arg_name)
        exclude_field_names = {name for names in excludes for name in names.split(self.delimiter) if name}

        if not include_field_names and not exclude_field_names:
            # No user fields filtering was requested, we have nothing to do here.
            return

        serializer_field_names = set(self.fields)

        fields_to_drop = serializer_field_names & exclude_field_names
        if include_field_names:
            fields_to_drop |= serializer_field_names - include_field_names

        for field in fields_to_drop:
            self.fields.pop(field)

    def get_method(self, request=None):
        req = request or self.get_request()
        return getattr(req, 'method', None)

    def get_request(self):
        try:
            return self.context['request']
        except (AttributeError, TypeError, KeyError):
            raise MisconfiguredSerializer('Either pass a request in context of serializer or override get request method')

    def get_query_params(self, request=None):
        req = request or self.get_request()
        try:
            query_params = req.query_params
        except AttributeError:
            # DRF 2
            query_params = getattr(req, 'QUERY_PARAMS', req.GET)

        return query_params