def get_all_poll_content_objects(model, **kwargs):
    return model.objects.all()


def get_published_pages_objects(model, site, **kwargs):
    return model.objects.published(site).filter(publisher_is_draft=False)
